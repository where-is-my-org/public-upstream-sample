# Collaborator Inventory

- 此工具會讀取 GitHub repository inventory CSV，逐一呼叫 GitHub REST API 取得每個 repository 的 all collaborators 與 direct collaborators，並輸出一份新增欄位後的 CSV
- 預設輸出檔名為 `<原 csv 檔名>-updated.csv`

## 檔案

| 檔案 | 說明 |
|------|------|
| `collaborator_inventory.py` | 主要 Python 腳本 |
| `requirements.txt` | Python 套件需求 |
| `README.md` | 使用說明 |

## CSV 輸入格式

輸入 CSV 至少須包含以下欄位：

| 欄位 | 說明 |
|------|------|
| `Org_Name` | GitHub organization 名稱 |
| `Repo_Name` | Repository 名稱 |

其他欄位會原封不動保留於輸出 CSV

## 取得的資料

每個 repository 會呼叫下列兩個 GitHub REST API：

| API | 說明 |
|-----|------|
| `GET /repos/{organization}/{repository}/collaborators` | 取得 all collaborators，包含 direct assign 與上層繼承的 collaborators |
| `GET /repos/{organization}/{repository}/collaborators?affiliation=direct` | 取得 direct collaborators |

腳本會自動處理 GitHub API pagination，每頁最多讀取 100 筆，直到所有 collaborator 讀取完成

## 輸出欄位

輸出 CSV 會保留原本所有欄位，並新增以下欄位：

| 欄位 | 說明 |
|------|------|
| `direct_collaborators` | direct collaborators JSON 陣列 |
| `all_collaborators` | all collaborators JSON 陣列 |

`direct_collaborators` 與 `all_collaborators` 會以 JSON 字串存入 CSV 欄位，內容僅保留 GitHub API 回傳的 `login` 與 `role_name`

## 權限需求

- 用具備目標 repository collaborator 查詢權限的 GitHub token
- 此腳本使用的 `List repository collaborators` API 要求 authenticated user 對 repository 具備 `write`、`maintain` 或 `admin` 權限
- 若 repository 屬於 organization，authenticated user 也必須是該 organization 的成員

若使用 OAuth app tokens 或 personal access tokens classic，token 需要包含以下 scopes：

| Token 類型 | 必要 scopes |
|------------|-------------|
| OAuth app token | `read:org`、`repo` |
| Personal access token classic | `read:org`、`repo` |

若使用 fine-grained access token，此 endpoint 支援以下 token 類型：

| Token 類型 | 必要 repository permissions |
|------------|-----------------------------|
| GitHub App user access token | `Metadata: read` |
| GitHub App installation access token | `Metadata: read` |
| Fine-grained personal access token | `Metadata: read` |

若使用 fine-grained personal access token，請確認 token 已授權目標 organization 與 repositories，並具備 `Metadata` repository permissions 的 read 權限

## 安裝

建議在專案根目錄建立 Python virtual environment 後安裝套件：

```bash
cd collaborator-inventory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用方式

可透過環境變數提供 token：

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
python collaborator_inventory.py ../xxx.csv
```

也可以直接以參數提供 token：

```bash
python collaborator_inventory.py ../xxx.csv --token "YOUR_GITHUB_TOKEN"
```

指定輸出檔案位置：

```bash
python collaborator_inventory.py ../xxx.csv --output ./result.csv
```

若遇到 GitHub API rate limit，並希望腳本等待 reset 後繼續執行，可加入：

```bash
python collaborator_inventory.py ../xxx.csv --wait-rate-limit
```

## Token 環境變數讀取順序

若未提供 `--token`，腳本會依序讀取以下環境變數：

1. `GITHUB_TOKEN`
2. `GH_TOKEN`
3. `GH_SOURCE_PAT`

## 錯誤處理

若某個 repository API 呼叫失敗，腳本不會中止整份 CSV 的處理，而是：

1. 將該 repository 的 collaborator 欄位填入空陣列
2. 將錯誤訊息輸出至 stderr
3. 繼續處理下一個 repository

常見錯誤包含 token 權限不足、repository 不存在、API rate limit 或網路連線逾時