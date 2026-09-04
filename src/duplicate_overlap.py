"""Engine 4: Duplicate / Overlap Detection (Weight: 15%)

Locked Architecture:
1. Candidate Blocking BEFORE embeddings:
   Groups works by (state, constituency or district, category) to avoid O(N^2) explosion.
2. Semantic Embeddings via all-MiniLM-L6-v2:
   Embeddings are computed only for the candidate works within the blocked pool.
   Cosine similarity evaluates semantic alignment on normalized work descriptions.
3. Agency/Entity Similarity via RapidFuzz:
   RapidFuzz token_set_ratio evaluates similarity between implementing authorities / IDAs / MPs.
4. Contextual Agreement:
   State / constituency / district agreement, amount tolerance, date proximity.
5. Tri-state Classification:
   - "Likely duplicate": Strong semantic similarity + contextual agreement (same MP / high agency match, similar amount),
     or verbatim semantic similarity inside the same block.
   - "Possible overlap": Moderate semantic similarity within the same block.
   - "Unrelated": Below similarity threshold or incompatible context.
6. Strictly avoids GPS / latitude-longitude.

NOTE: Similarity thresholds are first-pass calibrated/tunable prototype values,
NOT locked specification constants or statistically validated probabilities.
"""

from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


class DuplicateOverlapEngine:
    """Detects duplicate and overlapping works via contextual blocking, all-MiniLM-L6-v2 semantic embeddings, and RapidFuzz entity matching."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        semantic_threshold_likely: float = 0.82,
        semantic_threshold_possible: float = 0.68,
        semantic_verbatim_threshold: float = 0.95,
        entity_fuzzy_threshold: float = 80.0,
        amount_tolerance: float = 0.15,
        max_block_size: int = 500,
        encoder: Optional[Any] = None
    ):
        # Configurable first-pass calibrated heuristics (not locked constants)
        self.model_name = model_name
        self.semantic_threshold_likely = semantic_threshold_likely
        self.semantic_threshold_possible = semantic_threshold_possible
        self.semantic_verbatim_threshold = semantic_verbatim_threshold
        self.entity_fuzzy_threshold = entity_fuzzy_threshold
        self.amount_tolerance = amount_tolerance
        self.max_block_size = max_block_size

        self.encoder = encoder
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self.blocks: Dict[Tuple, List[Dict[str, Any]]] = defaultdict(list)
        self.work_to_block_key: Dict[Any, Tuple] = {}

    def _get_encoder(self):
        """Lazily loads the all-MiniLM-L6-v2 SentenceTransformer model."""
        if self.encoder is None:
            if SentenceTransformer is not None:
                self.encoder = SentenceTransformer(self.model_name)
            else:
                self.encoder = "fallback_text"
        return self.encoder

    def _get_blocking_key(self, work: Dict[str, Any]) -> Optional[Tuple]:
        """Generates contextual block key: (state, constituency or district, category)."""
        st = work.get("state")
        cat = work.get("category")
        loc = work.get("constituency") or work.get("district")
        if st and cat and loc:
            if not (isinstance(st, float) and np.isnan(st)) and not (isinstance(cat, float) and np.isnan(cat)) and not (isinstance(loc, float) and np.isnan(loc)):
                return (str(st).strip().lower(), str(loc).strip().lower(), str(cat).strip().lower())
        return None

    def build_index(self, works: List[Dict[str, Any]]) -> "DuplicateOverlapEngine":
        """Partitions works into contextual blocks before any embedding computation."""
        self.blocks.clear()
        self.work_to_block_key.clear()

        for w in works:
            dtl_id = w.get("work_recommendation_dtl_id")
            desc = w.get("work_description")
            if not dtl_id or not desc:
                continue

            key = self._get_blocking_key(w)
            if key:
                self.blocks[key].append(w)
                self.work_to_block_key[dtl_id] = key

        return self

    def _encode_descriptions(self, texts: List[str]) -> np.ndarray:
        """Encodes texts using all-MiniLM-L6-v2 with in-memory caching."""
        encoder = self._get_encoder()
        if encoder == "fallback_text" or encoder is None:
            return None

        to_encode = []
        indices_to_encode = []
        embeddings = [None] * len(texts)

        for i, t in enumerate(texts):
            norm_t = " ".join(t.lower().split())
            if norm_t in self._embedding_cache:
                embeddings[i] = self._embedding_cache[norm_t]
            else:
                to_encode.append(norm_t)
                indices_to_encode.append(i)

        if to_encode:
            encoded_vecs = encoder.encode(to_encode, convert_to_numpy=True, show_progress_bar=False)
            # Normalize vectors for fast cosine dot products
            norms = np.linalg.norm(encoded_vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            normalized_vecs = encoded_vecs / norms

            for idx, text, vec in zip(indices_to_encode, to_encode, normalized_vecs):
                self._embedding_cache[text] = vec
                embeddings[idx] = vec

        return np.vstack(embeddings)

    def _compute_cosine_similarities(self, target_text: str, candidate_texts: List[str]) -> Optional[List[float]]:
        """Computes semantic cosine similarity between target and all candidates in the block."""
        try:
            target_vec = self._encode_descriptions([target_text])
            if target_vec is None:
                return None
            cand_vecs = self._encode_descriptions(candidate_texts)
            if cand_vecs is None:
                return None
            # Target is 1x384, cand_vecs is Kx384 -> dot product is K
            sims = np.dot(cand_vecs, target_vec.T).flatten()
            return [float(np.clip(s, 0.0, 1.0)) for s in sims]
        except Exception:
            return None

    def _compute_agency_similarity(self, auth_a: Optional[str], auth_b: Optional[str]) -> float:
        """Computes RapidFuzz similarity between implementing agencies / authorities."""
        if not auth_a or not auth_b:
            return 0.0
        if fuzz is not None:
            return float(fuzz.token_set_ratio(auth_a, auth_b))
        tokens_a = set(auth_a.lower().split())
        tokens_b = set(auth_b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b) * 100.0

    def evaluate_work(
        self,
        work: Dict[str, Any],
        candidate_pool: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Evaluates duplicate/overlap risk for a work within its contextual candidate block.

        Returns:
          score (0-100 float)
          top_matches (list of candidate matches with similarity and classification)
          match_count_likely (int)
          match_count_possible (int)
          reason_codes (list[str])
          evidence (str)
          coverage (str)
        """
        dtl_id = work.get("work_recommendation_dtl_id")
        desc = work.get("work_description")

        if not desc or len(desc.strip()) < 5:
            return {
                "score": None,
                "available": False,
                "top_matches": [],
                "match_count_likely": 0,
                "match_count_possible": 0,
                "candidates_evaluated": 0,
                "reason_codes": ["DUPLICATE_INSUFFICIENT_TEXT"],
                "evidence": "Work description too short for duplicate/overlap detection.",
                "coverage": "missing_description"
            }

        # 1. Retrieve candidates strictly via contextual blocking
        candidates = []
        if candidate_pool is not None:
            candidates = candidate_pool
        else:
            block_key = self.work_to_block_key.get(dtl_id) or self._get_blocking_key(work)
            if block_key and block_key in self.blocks:
                candidates = [c for c in self.blocks[block_key] if c.get("work_recommendation_dtl_id") != dtl_id]

        if not candidates:
            return {
                "score": None,
                "available": False,
                "top_matches": [],
                "match_count_likely": 0,
                "match_count_possible": 0,
                "candidates_evaluated": 0,
                "reason_codes": ["DUPLICATE_NO_BLOCK_CANDIDATES"],
                "evidence": "Duplicate detection unavailable: no other candidate works in the same contextual block (state, constituency/district, category).",
                "coverage": "block_empty"
            }

        # Cap candidates if block is unusually large to preserve bounded latency
        candidates = candidates[:self.max_block_size]
        cand_descriptions = [c.get("work_description", "") for c in candidates]

        # 2. Semantic embeddings path via all-MiniLM-L6-v2 (computed only inside the block)
        cosine_sims = self._compute_cosine_similarities(desc, cand_descriptions)

        amt_work = work.get("amount_recommended") or 0.0
        mp_work = str(work.get("mp_name") or "").strip().lower()
        auth_work = work.get("implementing_authority") or work.get("ida_name")

        matches = []
        likely_count = 0
        possible_count = 0

        for idx, cand in enumerate(candidates):
            cand_desc = cand.get("work_description")
            if not cand_desc:
                continue

            cand_dtl = cand.get("work_recommendation_dtl_id")
            cand_amt = cand.get("amount_recommended") or 0.0
            cand_mp = str(cand.get("mp_name") or "").strip().lower()
            cand_auth = cand.get("implementing_authority") or cand.get("ida_name")

            # Semantic similarity (primary path)
            if cosine_sims is not None and idx < len(cosine_sims):
                semantic_sim = cosine_sims[idx]
            else:
                # Fallback text similarity if embedding model unavailable
                if fuzz is not None:
                    semantic_sim = float(fuzz.token_set_ratio(desc, cand_desc)) / 100.0
                else:
                    set_a, set_b = set(desc.lower().split()), set(cand_desc.lower().split())
                    semantic_sim = len(set_a & set_b) / len(set_a | set_b) if (set_a | set_b) else 0.0

            # RapidFuzz entity/agency similarity
            agency_sim = self._compute_agency_similarity(auth_work, cand_auth)

            # MP contextual agreement
            same_mp = (mp_work != "" and mp_work == cand_mp)

            # Amount agreement
            if amt_work > 0 and cand_amt > 0:
                amt_diff_ratio = abs(amt_work - cand_amt) / max(amt_work, cand_amt)
                similar_amt = amt_diff_ratio <= self.amount_tolerance
            else:
                similar_amt = False
                amt_diff_ratio = 1.0

            # Combined Classification using semantic similarity + contextual agreement
            if semantic_sim >= self.semantic_verbatim_threshold:
                # Verbatim or near-identical text inside same block
                classification = "Likely duplicate"
                likely_count += 1
                match_weight = 90.0
            elif semantic_sim >= self.semantic_threshold_likely and (same_mp or agency_sim >= self.entity_fuzzy_threshold or similar_amt):
                # Strong semantic match with contextual agreement
                classification = "Likely duplicate"
                likely_count += 1
                match_weight = 85.0
            elif semantic_sim >= self.semantic_threshold_possible:
                # Moderate semantic match within same block
                classification = "Possible overlap"
                possible_count += 1
                match_weight = 60.0 if (same_mp or similar_amt) else 45.0
            else:
                classification = "Unrelated"
                match_weight = 0.0

            if classification != "Unrelated":
                matches.append({
                    "matched_work_dtl_id": cand_dtl,
                    "matched_unique_work_number": cand.get("unique_work_number"),
                    "matched_work_description": cand_desc[:120],
                    "matched_amount": cand_amt,
                    "matched_mp_name": cand.get("mp_name"),
                    "matched_agency": cand_auth,
                    "semantic_cosine_similarity": round(semantic_sim, 3),
                    "agency_similarity": round(agency_sim, 1),
                    "same_mp": same_mp,
                    "similar_amount": similar_amt,
                    "amount_difference_ratio": round(amt_diff_ratio, 3),
                    "classification": classification,
                    "match_weight": match_weight
                })

        matches.sort(key=lambda m: (-m["match_weight"], -m["semantic_cosine_similarity"]))
        top_matches = matches[:5]

        # Calculate module score
        reason_codes = []
        if likely_count > 0:
            top_weight = top_matches[0]["match_weight"]
            score = min(100.0, top_weight + min(10.0, (likely_count - 1) * 3.0))
            reason_codes.append("DUPLICATE_LIKELY_MATCH_FOUND")
            if likely_count > 1:
                reason_codes.append("DUPLICATE_MULTIPLE_LIKELY_MATCHES")
        elif possible_count > 0:
            top_weight = top_matches[0]["match_weight"]
            score = min(75.0, top_weight + min(15.0, (possible_count - 1) * 2.0))
            reason_codes.append("DUPLICATE_POSSIBLE_OVERLAP_FOUND")
        else:
            score = 0.0
            reason_codes.append("DUPLICATE_NONE_FOUND")

        score = round(min(100.0, max(0.0, score)), 2)

        # Build evidence narrative
        if top_matches:
            top_m = top_matches[0]
            evidence = (
                f"Found {likely_count} likely duplicate(s) and {possible_count} possible overlap(s) "
                f"within block (n={len(candidates)}). Top match: DTL_ID {top_m['matched_work_dtl_id']} "
                f"({top_m['classification']}, semantic cosine: {top_m['semantic_cosine_similarity']:.3f}, "
                f"agency sim: {top_m['agency_similarity']}%, same MP: {top_m['same_mp']}, amount match: {top_m['similar_amount']}). "
                f"Description: '{top_m['matched_work_description']}'"
            )
        else:
            evidence = f"Evaluated against {len(candidates)} candidate works in block using all-MiniLM-L6-v2 embeddings. No duplicates or overlaps detected."

        return {
            "score": score,
            "available": True,
            "top_matches": top_matches,
            "match_count_likely": likely_count,
            "match_count_possible": possible_count,
            "candidates_evaluated": len(candidates),
            "reason_codes": reason_codes,
            "evidence": evidence,
            "coverage": "blocked_minilm_semantic" if cosine_sims is not None else "blocked_text_fallback"
        }
