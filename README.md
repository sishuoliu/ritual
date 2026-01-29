# ritul

Repository for the **佛教经济学桌游** (Buddhist Economics Board Game) project and related materials.

- **桌游/** — Board game design and simulation (功德轮回 · 救赎之路)
- **resources/** — Academic references (Economics of Salvation, merit transfer, etc.)
- Root `.txt` / `.pdf` — Presentation and reading materials

## Quick start

### 功德轮回：众生百态 (Merit Cycle) — simulation & tuning

From repo root (recommended, avoids path encoding issues):

```bash
python run_merit_cycle_tuning.py
```

This runs the balance tuning script in `桌游/模拟测试/` (see `桌游/README.md`).

### 救赎之路 (Path to Salvation)

See `桌游/README.md` and `桌游/终版/` for rulebooks and release packages.

## Repository structure

```
ritul/
├── README.md                 # This file
├── .gitignore
├── run_merit_cycle_tuning.py # Launcher for 功德轮回 balance tuning
├── 桌游/                     # Board game project (main)
│   ├── README.md             # Project overview & structure
│   ├── 设计提案/             # 功德轮回 design docs & v3.6 rules
│   ├── 模拟测试/             # 功德轮回 simulator & backtest
│   ├── 终版/                 # 救赎之路 release packages
│   ├── 03_测试报告/           # Historical test reports
│   ├── 05_游戏规则/          # 救赎之路 rule variants
│   └── 06_其他游戏设计/      # Other game design
└── resources/                # Academic PDFs & extracts
```

## 上传到 GitHub（首次）

在项目根目录执行：

```bash
git init
git add .
git commit -m "Initial: 桌游项目与功德轮回 v3.6"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

`.gitignore` 已忽略 `__pycache__/`、`tuning_results*.json`、`*.log` 等。更多说明见 `桌游/开发说明.md` 与 `桌游/文件整理说明.txt`。

## License & contact

See project docs in `桌游/`. For issues or contributions, use the repository’s issue tracker.

*Last updated: 2026-01-28*
