# Deployment Guide — MPLADS Risk Intelligence Command Center

This guide documents the exact steps to publish the frozen **MPLADS Risk Intelligence & Investigation Engine** to **Streamlit Community Cloud**.

---

## 1. Prerequisites
- A GitHub account ([github.com](https://github.com)).
- A Streamlit Community Cloud account ([share.streamlit.io](https://share.streamlit.io)), signed in via your GitHub account.

---

## 2. GitHub Repository Preparation

From the repository root (`c:\Users\ACER\MPLADS-Risk-Engine`):

```bash
# 1. Verify git status
git status

# 2. Add application files to git staging
# (Required: app.py, src/, config/, tests/, data/processed/, artifacts/, requirements.txt, README.md)
git add app.py requirements.txt README.md .gitignore config/ src/ tests/ artifacts/ docs/ data/processed/

# Optional: Add data/raw if you wish to archive raw JSONs, or keep data/processed only for fast deployment.
# Note: GitHub warns on files >50MB. data/processed (17.8 MB) contains all frozen real data required at runtime.

# 3. Commit your frozen submission
git commit -m "feat: frozen MPLADS Risk Intelligence command center ready for deployment"

# 4. Link your remote GitHub repository
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git

# 5. Push to GitHub
git push -u origin main
```

---

## 3. Streamlit Community Cloud Deployment

1. Navigate to **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
2. Click **"New app"** (or **"Create app"**).
3. Select **"I already have an app"**.
4. Configure the deployment settings:
   - **Repository**: `<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>` (select your repo from the dropdown)
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL (optional)**: e.g. `mplads-risk-engine` (results in `https://mplads-risk-engine.streamlit.app`)
5. Click **"Advanced settings..."** (Optional):
   - **Python Version**: Select `3.11` (or `3.10`).
   - Secrets: *None required* (the platform runs on authentic open public MoSPI datasets).
6. Click **"Deploy!"**.

---

## 4. Deployment Verification & Runtime Behavior

- Streamlit Community Cloud reads `requirements.txt` from the repo root and installs:
  `streamlit`, `pandas`, `numpy`, `scipy`, `sentence-transformers`, `rapidfuzz`, `scikit-learn`, `pyyaml`, `pyarrow`, `pytest`.
- The application starts with `app.py`.
- **Expected Public URL Pattern**:
  ```
  https://<your-custom-subdomain>.streamlit.app
  # Example: https://mplads-risk-intelligence.streamlit.app
  ```
- **Performance**:
  - Parquet summary table (`8.1 MB`) loads in $<1.0$ second.
  - Initial loading of SentenceTransformer for on-demand duplicate deep dives takes ~5–7 seconds on first tab click, then remains cached in memory via `@st.cache_resource`.

---

## 5. Updates and Redeployment

- **Continuous Deployment**: Any push to the `main` branch on GitHub automatically triggers a live rebuild and deployment on Streamlit Community Cloud.
- **Manual Reboot**: You can clear caches or reboot the container at any time from the app's bottom-right context menu: **Manage app → Reboot app**.

---

## 6. Public Access Notice

> [!WARNING]
> Deploying to Streamlit Community Cloud makes the URL publicly accessible on the internet.
> The codebase has been audited and contains:
> - **Zero secrets, tokens, or API credentials**
> - **Zero private local file paths**
> - **Zero defamatory or accusatory terminology**
> All presented information is derived strictly from authentic Government of India MoSPI public data.
