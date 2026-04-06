# 遷移至 GitHub Enterprise Managed Users 完整指南 - 第 4 部分：安全性與合規性

> **📚 系列：遷移至 GitHub Enterprise Managed Users 完整指南**
> 這是 EMU 遷移指南系列的**第 4 部分，共 6 部分**。
>
> | 部分 | 主題 |
> |------|------|
> | [第 1 部分：探索與決策](Part1-Discovery&Decision.md) | 定義目標、評估適用性、取得共識 |
> | [第 2 部分：遷移前準備](Part2-Pre-MigrationPreparation.md) | 盤點、清理、IdP 準備、使用者溝通 |
> | [第 3 部分：身分識別與存取設定](Part3-Identity&Access%20Setup.md) | 設定 SCIM、佈建使用者、建立團隊 |
> | **[第 4 部分：安全性與合規性](Part4-Security&Compliance.md)**（您在此處）| 稽核記錄、安全強化、CI/CD、整合 |
> | [第 5 部分：遷移執行](Part5-MigrationExecution.md) | 執行 GEI、遷移儲存庫 |
> | [第 6 部分：驗證與採用](Part6-Validation&Adoption.md) | 測試、使用者培訓、OSS 策略、正式上線 |

---

# 第 4 階段：安全性與合規性

*在遷移開始前鎖定新環境。*

在你開始搬移儲存庫和引導使用者上線之前，你需要先建立安全防護措施。這個階段涵蓋稽核記錄、企業政策、CI/CD 設定和整合。先把這些做對，這樣當程式碼進入新環境時，就已經受到保護了。

## 稽核記錄與合規性

EMU 提供詳細的稽核記錄，對合規性和安全監控至關重要。

### 合規框架對應

EMU 的控制措施與常見的合規框架有良好的對應。以下是 EMU 功能如何支援特定要求：

| 框架 | 相關控制 | EMU 如何提供幫助 |
|------|----------|-----------------|
| **SOC 2** | Access Control (CC6.1)、User Authentication (CC6.6) | 集中式 IdP 身分驗證、自動取消佈建、稽核軌跡 |
| **HIPAA** | Access Controls (164.312(a))、Audit Controls (164.312(b)) | 透過 IdP 群組進行角色型存取、詳細稽核記錄 |
| **FedRAMP** | IA-2 (Identification)、AC-2 (Account Management) | SSO 強制執行、自動化帳號生命週期、Session 管理 |
| **PCI-DSS** | Requirement 7 (Restrict Access)、Requirement 8 (Identify Users) | 唯一使用者 ID、透過 IdP 的 MFA、存取記錄 |
| **GDPR** | Article 32 (Security of Processing) | 資料駐留選項、存取控制、透過 IdP 的刪除權 |
| **ISO 27001** | A.9 (Access Control) | 身分管理、使用者佈建、存取審查 |

> 注意：這不代表你自動符合合規要求。這些是 EMU **幫助**你達到合規狀態的領域。

**關鍵合規效益：**
- **單一事實來源**：所有存取決策都從你的 IdP 流出，簡化了稽核證據的收集
- **自動化離職處理**：取消佈建的使用者會立即失去存取權限，無需手動清理
- **不可竄改的稽核軌跡**：GitHub 的稽核記錄提供所有操作的防竄改記錄
- **職責分離**：透過 IdP 群組進行角色型存取，確保適當的分離

### 記錄的內容

稽核記錄會擷取：
- 使用者身分驗證事件
- 儲存庫存取和修改
- 組織和團隊變更
- SAML SSO 和 SCIM 身分資訊
- 來源 IP 位址（啟用時）
- Token 型存取識別

事件保留 180 天，Git 事件保留 7 天。

### 串流稽核記錄

如需長期保留和 SIEM 整合，請設定稽核記錄串流：

```mermaid
flowchart LR
    GH[GitHub Enterprise] -->|Webhook| STREAM[Audit Log Stream]
    STREAM --> SPLUNK[Splunk]
    STREAM --> DATADOG[Datadog]
    STREAM --> SENTINEL[Azure Sentinel]
    STREAM --> S3[AWS S3]
    STREAM --> GCS[Google Cloud Storage]
    STREAM --> BLOB[Azure Blob Storage]
    style GH fill:#a5d6a7,stroke:#2e7d32,color:#333
    style STREAM fill:#b3e5fc,stroke:#0288d1,color:#333
    style SPLUNK fill:#ffe0b2,stroke:#e65100,color:#333
    style DATADOG fill:#ffe0b2,stroke:#e65100,color:#333
    style SENTINEL fill:#ffe0b2,stroke:#e65100,color:#333
    style S3 fill:#ffe0b2,stroke:#e65100,color:#333
    style GCS fill:#ffe0b2,stroke:#e65100,color:#333
    style BLOB fill:#ffe0b2,stroke:#e65100,color:#333
```

設定詳情請參閱 [Streaming the audit log for your enterprise](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/streaming-the-audit-log-for-your-enterprise)。

#### 啟用 API Request Event 串流

預設情況下，稽核記錄串流僅包含 Web（UI）事件。為了完整可見性，你還應該啟用 **API Request Events**。這些記錄了對你企業發出的每個 REST 和 GraphQL API 呼叫，這對於偵測自動化存取模式、識別設定錯誤的整合以及滿足合規要求至關重要。

要啟用 API Request Event 串流：
1. 導覽至你的企業設定 → Audit log → Log streaming
2. 選擇你已設定的串流
3. 勾選 **Enable API Request Events**

> **⚠️ 警告：** API Request Events 產生的資料量遠大於 Web 事件——根據你的自動化足跡，通常多出 10-100 倍。確保你的串流目的地可以處理增加的吞吐量，並且你已為額外的儲存和攝取成本做好預算。先在測試時段啟用以評估資料量，然後再正式啟用。

詳情請參閱 [Streaming the audit log for your enterprise - API request events](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/streaming-the-audit-log-for-your-enterprise#enabling-audit-log-streaming-of-api-requests)。

#### 啟用來源 IP 揭露

預設情況下，GitHub 稽核記錄事件不包含執行者的來源 IP 位址。為了安全監控、事件回應和合規性，你需要啟用 **IP source disclosure**，使每個稽核事件都包含來源 IP 位址。

要啟用來源 IP 揭露：
1. 導覽至你的企業設定 → Settings → Authentication security
2. 在 **IP allow list** 下，啟用 **Display IP addresses in audit log**

啟用後，你的稽核記錄事件將包含 `actor_ip` 欄位，這對以下用途非常有價值：
- **事件回應**：將可疑活動與已知 IP 範圍進行關聯
- **地理封鎖驗證**：確認存取僅來自預期的地點
- **Conditional Access Policy 執行**：驗證 Entra ID CAP 是否按預期運作
- **合規證據**：向稽核人員展示存取控制的執行情況

> **注意：** Enterprise 擁有者應該將此變更通知使用者，因為 IP 記錄可能根據所在司法管轄區有隱私影響。啟用前請諮詢你的法務和隱私團隊。

設定步驟請參閱 [Displaying IP addresses in the audit log for your enterprise](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/displaying-ip-addresses-in-the-audit-log-for-your-enterprise)。

### Audit Log API

如需以程式方式存取，請使用 Audit Log API：

```bash
# Get recent audit events
gh api \
  -H "Accept: application/vnd.github+json" \
  /enterprises/{enterprise}/audit-log
```

> 注意：建議將稽核記錄串流到其他地方進行資料處理，而不是呼叫 API，因為 API 有特定的速率限制，在繁忙的環境中可能無法跟上。

請參閱 [Using the audit log API for your enterprise](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/using-the-audit-log-api-for-your-enterprise)。

## 安全強化最佳實務

一旦完成遷移，實施適當的安全控制是必不可少的。

### Enterprise 政策

設定企業級政策以強制執行安全標準：

- **儲存庫可見性**：限制為僅限 Private 和 Internal
- **儲存庫建立**：控制誰可以建立儲存庫
- **Forking**：限制 Forking 僅在企業內
- **Actions 權限**：限制為已驗證或企業核准的 Actions
- **Code Security**：預設啟用 Secret Scanning 和 Code Scanning

請參閱 [Enforcing policies for your enterprise](https://docs.github.com/en/enterprise-cloud@latest/admin/enforcing-policies/enforcing-policies-for-your-enterprise)。

### Conditional Access Policies (OIDC)

如果你使用 OIDC 搭配 Entra ID，你可以強制執行特定的 Conditional Access Policies。OIDC 無法強制執行裝置健康/合規條件。

請參閱 [About support for your IdP's Conditional Access Policy](https://docs.github.com/en/enterprise-cloud@latest/admin/identity-and-access-management/using-enterprise-managed-users-for-iam/about-support-for-your-idps-conditional-access-policy)。

### Secret Scanning 和 Push Protection

如果你有 GitHub Advanced Security，請在企業層級啟用 Secret Scanning 和 Push Protection：

```
Enterprise Settings → Code security and analysis → Enable for all repositories
```

這會在密鑰被提交前攔截它們，並對任何漏網之魚發出警報。

### IP Allow Lists

限制從已知 IP 範圍存取你的企業：

```
Enterprise Settings → Authentication security → IP allow list
```

> 注意：這裡有一個注意事項，確保你與邊緣網路團隊交談以了解你的網際網路出口。嘗試將存取限制在非常少量的 IP 以簡化 Allow List 管理是很有誘惑力的，然而，這可能會產生觸發 GitHub 的 DDoS 保護和速率限制的負面效果。

## CI/CD 影響與 GitHub Actions

你的 CI/CD 流程在遷移期間需要關注。GitHub Actions 可以與 EMU 搭配使用，但有一些重要的差異和注意事項。

### GitHub Actions 變更

**保持不變的部分：**
- Workflow 語法和 YAML 結構
- GitHub-hosted Runner 可用性（針對 Organization 擁有的儲存庫）
- 大多數 Marketplace Actions 正常運作
- 企業內的 Reusable Workflows

**變更的部分：**
- **個人儲存庫 Runners**：Managed Users 無法對個人儲存庫使用 GitHub-hosted Runners（他們只能擁有 Private 儲存庫）
- **跨企業 Workflows**：無法引用企業外部的 Actions 或 Workflows，除非它們在公開儲存庫中
- **GITHUB_TOKEN 範圍**：Token 權限僅限於企業資源

### Runner 策略

對於 EMU 企業，請仔細規劃你的 Runner 基礎架構：

```mermaid
flowchart TB
    subgraph Enterprise["EMU Enterprise"]
        subgraph Org1["組織 A"]
            R1["GitHub-Hosted Runners"]
            SR1["Self-Hosted Runners<br/>（組織層級）"]
        end
        subgraph Org2["組織 B"]
            R2["GitHub-Hosted Runners"]
            SR2["Self-Hosted Runners<br/>（組織層級）"]
        end
        ER["Enterprise Runners<br/>（共用）"]
    end
    
    ER --> Org1
    ER --> Org2
    
    style Enterprise fill:#f0fff4,stroke:#28a745,color:#333
    style Org1 fill:#e8f5e9,stroke:#66bb6a,color:#333
    style Org2 fill:#e8f5e9,stroke:#66bb6a,color:#333
    style R1 fill:#b3e5fc,stroke:#0288d1,color:#333
    style SR1 fill:#ffe0b2,stroke:#e65100,color:#333
    style R2 fill:#b3e5fc,stroke:#0288d1,color:#333
    style SR2 fill:#ffe0b2,stroke:#e65100,color:#333
    style ER fill:#ce93d8,stroke:#7b1fa2,color:#333
```

**Self-hosted Runner 注意事項：**
- 在企業層級註冊 Runners 以用於共用基礎架構
- 使用 Runner Groups 來控制哪些組織可以使用哪些 Runners。這還有一個額外的好處，就是將使用與實際基礎架構分離。開發者設定 Workflows 在 Runner Group 上執行而無需擔心細節。維運團隊可以在不需要開發者更新 Workflows 的情況下替換底層硬體。
- 實施如 [Actions Runner Controller](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) 的自動擴展選項
- 確保如果 Workflows 需要企業資源，Runners 可以對你的 IdP 進行身分驗證

### Secrets 和 Variables 管理

EMU 的 Secrets 管理略有變化：

1. **Organization Secrets**：運作方式相同，範圍限於組織儲存庫
2. **Repository Secrets**：運作方式相同
3. **Environment Secrets**：運作方式相同，搭配 Environment Protection Rules
4. **Personal Access Tokens (PATs)**：Managed Users 可以建立 PATs，但範圍僅限於企業資源

**最佳實務：**
```yaml
# Use OIDC for cloud provider authentication instead of long-lived secrets
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-actions
          aws-region: us-east-1
```

請參閱 [About security hardening with OpenID Connect](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)。

### Actions 權限和政策

設定企業級 Actions 政策：

```
Enterprise Settings → Policies → Actions
```

安全 EMU 環境的建議設定：
- **Allow select actions**：限制為 GitHub 官方、已驗證的 Marketplace 和特定受信任的 Actions
- **Require approval for fork PRs**：防止來自 Forks 的惡意 Workflow 執行
- **Default workflow permissions**：設定為唯讀，要求明確的寫入權限
- **Allow GitHub Actions to create PRs**：除非特別需要，否則停用

### 遷移現有 Workflows

從標準 GHEC 遷移 Workflows 時：

1. **稽核 Action 來源**：確保所有引用的 Actions 在你的 EMU 企業中可用
2. **更新身分驗證**：將個人 PATs 替換為 GitHub App Tokens 或 OIDC
3. **審查外部呼叫**：呼叫外部 API 的 Workflows 可能需要更新憑證
4. **徹底測試**：在切換正式環境前在新環境中執行 Workflows

```bash
# Find all actions used in your workflows
find . -name "*.yml" -path ".github/workflows/*" -exec grep -h "uses:" {} \; | \
  sort | uniq -c | sort -rn
```

## 整合規劃

整合通常是 EMU 遷移中最複雜的部分。你需要稽核、測試並可能重新設定每個整合。

### 需要考慮的整合類型

```mermaid
flowchart LR
    subgraph GitHub["GitHub EMU Enterprise"]
        GHA["GitHub Apps"]
        OA["OAuth Apps"]
        WH["Webhooks"]
        API["API 整合"]
    end
    
    subgraph External["外部系統"]
        JIRA["Jira/專案管理"]
        SLACK["Slack/Teams"]
        CI["外部 CI/CD"]
        SEC["安全工具"]
        DOCK["Container Registries"]
    end
    
    GHA <--> JIRA
    GHA <--> SEC
    OA <--> SLACK
    WH --> CI
    API <--> DOCK
    
    style GitHub fill:#f0fff4,stroke:#28a745,color:#333
    style External fill:#f0f7ff,stroke:#0366d6,color:#333
    style GHA fill:#a5d6a7,stroke:#2e7d32,color:#333
    style OA fill:#a5d6a7,stroke:#2e7d32,color:#333
    style WH fill:#a5d6a7,stroke:#2e7d32,color:#333
    style API fill:#a5d6a7,stroke:#2e7d32,color:#333
    style JIRA fill:#bbdefb,stroke:#1565c0,color:#333
    style SLACK fill:#bbdefb,stroke:#1565c0,color:#333
    style CI fill:#bbdefb,stroke:#1565c0,color:#333
    style SEC fill:#bbdefb,stroke:#1565c0,color:#333
    style DOCK fill:#bbdefb,stroke:#1565c0,color:#333
```

### GitHub Apps 與 OAuth Apps

**GitHub Apps**（EMU 的首選）：
- 可以安裝在組織或儲存庫層級
- 使用具有特定權限的短期 Tokens
- 與 Managed User 限制配合良好
- 可以限制在特定儲存庫

**OAuth Apps**（謹慎使用）：
- 以使用者身分進行身分驗證，這限制了 Managed Users 的功能
- 可能與 EMU 的可見性限制有問題
- 考慮在可能的地方遷移到 GitHub Apps

### 整合稽核檢查清單

遷移前，記錄每個整合：

| 整合 | 類型 | 目前驗證方式 | EMU 相容 | 遷移步驟 |
|------|------|------------|----------|----------|
| Jira | GitHub App | App Installation | ✅ 是 | 在新企業重新安裝 |
| Jenkins | Webhook + PAT | Personal Token | ⚠️ 需更新 | 使用 GitHub App Token |
| Slack | OAuth App | User OAuth | ⚠️ 需測試 | 使用 Managed User 驗證 |
| SonarQube | GitHub App | App Installation | ✅ 是 | 重新安裝，更新設定 |
| 自訂工具 | API | Service Account | ❌ 需重做 | 建立 Machine User 或 GitHub App |

### 常見整合模式

**模式 1：GitHub App Installation**
```yaml
# Preferred approach - install app at org level
# App authenticates with installation token
# Works well with EMU
```

**模式 2：Machine User（用於舊版整合）**
如果你有需要「使用者」帳號的整合：
- 在 IdP 中佈建一個專用的 Managed User
- 指派最小必要權限
- 使用此帳號的 PAT 用於整合
- 透過稽核記錄監控使用情況

**模式 3：Webhook 到外部系統**
```bash
# Webhooks work the same in EMU
# Re-register webhooks after migration
# Update webhook secrets
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/orgs/ORG/hooks \
  -d '{"name":"web","config":{"url":"https://example.com/webhook"}}'
```

### 第三方工具相容性

聯繫供應商以驗證 EMU 相容性：
- **IDE 外掛**：VS Code、JetBrains 等
- **安全掃描**：Snyk、Checkmarx、Veracode
- **專案管理**：Jira、Azure Boards、Linear
- **溝通工具**：Slack、Microsoft Teams
- **監控**：Datadog、New Relic

大多數現代工具支援 GitHub Apps 且與 EMU 配合良好。問題通常出現在依賴使用者層級 OAuth 的舊版工具上。

## Token 遷移策略

Personal Access Tokens (PATs) 是 EMU 遷移中最容易被忽略的面向之一。在舊環境中綁定到個人帳號的每個 Token 都會失效。本節提供識別、規劃和遷移 Tokens 的完整方法。

### 了解 Token 問題

在標準 GHEC 中，PATs 綁定到個人帳號。當你遷移到 EMU 時：

- **舊 Tokens 停止運作**：它們綁定到不再有存取權限的帳號
- **必須建立新 Tokens**：由 EMU 企業中的 Managed Users 建立
- **自動化中斷**：CI/CD Pipelines、腳本和整合會失敗
- **Service Accounts 需要重新思考**：「共用 Service Account」模式的運作方式不同

```mermaid
flowchart LR
    subgraph Before["遷移前"]
        PA["個人帳號<br/>dev@company.com"]
        PAT1["PAT: ghp_xxx<br/>(CI/CD)"]
        PAT2["PAT: ghp_yyy<br/>(腳本)"]
        PA --> PAT1
        PA --> PAT2
    end
    
    subgraph After["遷移後"]
        MA["Managed User<br/>dev_acme"]
        NPAT["新 PAT: ghp_zzz"]
        GA["GitHub App<br/>（首選）"]
        MA --> NPAT
        GA -.->|"Installation Token"| API["API 存取"]
    end
    
    Before -->|"遷移"| After
    PAT1 -.->|"❌ 無效"| X1["中斷"]
    PAT2 -.->|"❌ 無效"| X2["中斷"]
    
    style Before fill:#fff3e0,stroke:#f57c00,color:#333
    style After fill:#e8f5e9,stroke:#388e3c,color:#333
    style X1 fill:#ffebee,stroke:#c62828,color:#333
    style X2 fill:#ffebee,stroke:#c62828,color:#333
    style PA fill:#ffe0b2,stroke:#e65100,color:#333
    style PAT1 fill:#ffe0b2,stroke:#e65100,color:#333
    style PAT2 fill:#ffe0b2,stroke:#e65100,color:#333
    style MA fill:#a5d6a7,stroke:#2e7d32,color:#333
    style NPAT fill:#a5d6a7,stroke:#2e7d32,color:#333
    style GA fill:#a5d6a7,stroke:#2e7d32,color:#333
    style API fill:#a5d6a7,stroke:#2e7d32,color:#333
```

### 步驟 1：盤點現有 Tokens

在遷移 Tokens 之前，你需要知道目前有哪些。不幸的是，沒有 API 可以列出組織中的所有 PATs（這是設計使然——它是一個安全功能）。你需要多管齊下的方式：

**稽核記錄分析**

在稽核記錄中搜尋 Token 使用模式：

```bash
# Export audit log entries for token-related events
gh api orgs/YOUR_ORG/audit-log \
  --paginate \
  -X GET \
  -f phrase='action:oauth_access.create OR action:personal_access_token.create' \
  --jq '.[] | {actor: .actor, action: .action, created_at: .created_at}' \
  > token_audit.json

# Look for API authentication patterns
gh api orgs/YOUR_ORG/audit-log \
  --paginate \
  -X GET \
  -f phrase='action:repo.download_zip' \
  --jq '.[] | {actor: .actor, actor_ip: .actor_ip, created_at: .created_at}' \
  > api_usage.json
```

**調查你的團隊**

建立一個 Token 盤點表單讓團隊回報：

| Token 用途 | 擁有者 | 範圍 | 使用位置 | 到期日 | 遷移計畫 |
|-----------|--------|------|----------|--------|----------|
| Jenkins CI | @devops-team | repo, workflow | Jenkins 伺服器 | 永不 | 轉換為 GitHub App |
| 部署腳本 | @platform | repo, packages | deploy.sh | 2025-06-01 | 新 Managed User PAT |
| Slack 整合 | @integrations | repo:status | Slack App 設定 | 永不 | 使用 GitHub App for Slack |
| 個人自動化 | @jsmith | repo, gist | 本地腳本 | 永不 | 使用者建立新 PAT |

**檢查 CI/CD 設定**

掃描你的儲存庫中硬編碼或引用的 Tokens：

```bash
# Search for PAT references in workflow files
gh api search/code \
  -X GET \
  -f q='org:YOUR_ORG filename:.yml path:.github/workflows GITHUB_TOKEN OR ghp_ OR github_pat_' \
  --jq '.items[] | {repo: .repository.full_name, path: .path}'

# Check for secrets references
gh api search/code \
  -X GET \
  -f q='org:YOUR_ORG secrets. filename:.yml' \
  --jq '.items[] | {repo: .repository.full_name, path: .path}'
```

### 步驟 2：依遷移路徑分類 Tokens

不是所有 Tokens 都要以相同方式遷移。對每個 Token 進行分類：

| 分類 | 描述 | 遷移路徑 |
|------|------|----------|
| **轉換為 GitHub App** | 自動化、CI/CD、整合 | 建立/安裝 GitHub App |
| **Machine User PAT** | Service Accounts、共用自動化 | 佈建專用 Managed User |
| **個人使用者 PAT** | 個人腳本、IDE 身分驗證 | 使用者在遷移後建立新 PAT |
| **淘汰** | 未使用、重複或過時 | 不遷移 |

### 步驟 3：為自動化建立 GitHub Apps

對於大多數自動化使用案例，GitHub Apps 是首選解決方案。它們提供：

- **細粒度權限**：只要求你需要的權限
- **短期 Tokens**：Installation Tokens 在 1 小時後過期
- **稽核軌跡**：所有操作都歸屬於該 App
- **不依賴使用者**：無論使用者變更，App 都會持續運作

**建立用於 CI/CD 的 GitHub App**

```bash
# Create a GitHub App via the UI or API
# Navigate to: Enterprise Settings → GitHub Apps → New GitHub App

# Required permissions for typical CI/CD:
# - Contents: Read and write (clone, push)
# - Pull requests: Read and write (create PRs, add comments)
# - Workflows: Read and write (trigger workflows)
# - Checks: Read and write (report status)
# - Metadata: Read (required for all apps)
```

**產生 Installation Tokens**

```bash
#!/bin/bash
# generate-installation-token.sh
# Generates a short-lived installation token for a GitHub App

APP_ID="YOUR_APP_ID"
INSTALLATION_ID="YOUR_INSTALLATION_ID"
PRIVATE_KEY_PATH="path/to/private-key.pem"

# Generate JWT
now=$(date +%s)
iat=$((now - 60))
exp=$((now + 600))

header=$(echo -n '{"alg":"RS256","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
payload=$(echo -n "{\"iat\":${iat},\"exp\":${exp},\"iss\":\"${APP_ID}\"}" | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')

signature=$(echo -n "${header}.${payload}" | openssl dgst -sha256 -sign "${PRIVATE_KEY_PATH}" | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')

jwt="${header}.${payload}.${signature}"

# Get installation token
curl -s -X POST \
  -H "Authorization: Bearer ${jwt}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/app/installations/${INSTALLATION_ID}/access_tokens" \
  | jq -r '.token'
```

**在 GitHub Actions 中使用 Installation Tokens**

```yaml
# .github/workflows/deploy.yml
name: Deploy with GitHub App

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Generate GitHub App Token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ vars.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
          owner: ${{ github.repository_owner }}
      
      - name: Checkout with App Token
        uses: actions/checkout@v4
        with:
          token: ${{ steps.app-token.outputs.token }}
      
      - name: Push changes
        run: |
          git config user.name "my-automation-app[bot]"
          git config user.email "123456+my-automation-app[bot]@users.noreply.github.com"
          # ... make changes ...
          git push
        env:
          GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}
```

### 步驟 4：為舊版整合設定 Machine Users

有些整合就是無法使用 GitHub Apps——它們需要 PAT。對於這些情況，建立專用的「Machine Users」（專門用於自動化的 Managed User 帳號）：

**佈建 Machine User**

1. **在 IdP 中建立專用身分**
   - 使用描述性名稱：`svc-github-jenkins`、`bot-deploy-automation`
   - 使用群組信箱或通訊群組清單作為電子郵件
   - 在 IdP 中指派至 GitHub EMU 應用程式

2. **SCIM 在 GitHub 上佈建帳號**
   - 使用者名稱將類似 `svc-github-jenkins_acme`
   - 帳號像其他使用者一樣被管理

3. **為 Machine User 建立 PAT**
   - 以 Machine User 身分登入（你需要 IdP 憑證）
   - 產生具有最小必要權限的 Fine-Grained PAT
   - 設定適當的到期日（並在日曆上設定輪換提醒！）

4. **安全地儲存 Token**
   - 使用密鑰管理工具（Vault、Azure Key Vault、AWS Secrets Manager）
   - 永遠不要將 Tokens 提交到儲存庫
   - 實施 Token 輪換程序

**Machine User 最佳實務**

| 實務 | 原因 |
|------|------|
| 每個整合使用一個 Machine User | 隔離、更容易稽核、更簡單的撤銷 |
| 最小權限 | 最小權限原則 |
| 描述性命名 | 使用 `svc-*` 或 `bot-*` 前綴以便識別 |
| Token 到期 | 最長 90 天，搭配輪換流程 |
| 記錄擁有權 | 必須有人對每個 Machine User 負責 |
| 定期存取審查 | 納入季度存取認證 |

### 步驟 5：Fine-Grained PATs 與 Classic PATs

EMU 支援兩種 Token 類型，但強烈建議使用 Fine-Grained PATs：

| 功能 | Classic PAT | Fine-Grained PAT |
|------|-------------|------------------|
| 權限細粒度 | 廣泛範圍 | 每個儲存庫、特定權限 |
| 到期日 | 選用 | 必須（最長 1 年） |
| 核准流程 | 無 | 選用（組織可要求） |
| 資源存取 | 所有可存取的儲存庫 | 明確選擇的儲存庫 |
| 稽核可見性 | 有限 | 詳細 |

**啟用 Fine-Grained PAT 控制**

```bash
# Require approval for fine-grained PATs (recommended)
gh api orgs/YOUR_ORG \
  -X PATCH \
  -f personal_access_token_requests_enabled=true

# Restrict classic PAT access (optional but recommended)
# This can be done via Enterprise Settings → Policies → Personal access tokens
```

**建立 Fine-Grained PAT**

```bash
# Via UI: Settings → Developer settings → Personal access tokens → Fine-grained tokens

# Recommended settings:
# - Expiration: 90 days or less
# - Repository access: Only select repositories
# - Permissions: Minimum required for the use case
```

### 步驟 6：更新使用者

建立新 Tokens 後，更新所有使用者：

**CI/CD Pipelines**

```yaml
# Before: Using personal PAT stored in org secrets
env:
  GITHUB_TOKEN: ${{ secrets.DEPLOY_PAT }}

# After: Using GitHub App installation token
- uses: actions/create-github-app-token@v1
  id: app-token
  with:
    app-id: ${{ vars.DEPLOY_APP_ID }}
    private-key: ${{ secrets.DEPLOY_APP_KEY }}
```

**外部系統**

| 系統 | 更新位置 | 備註 |
|------|----------|------|
| Jenkins | Credentials Store | 更新 GitHub 伺服器設定 |
| ArgoCD | Repository Secrets | 更新所有儲存庫憑證 |
| Terraform | Provider Config 或環境變數 | 可能需要 State 遷移 |
| 腳本 | 環境變數 | 更新部署文件 |

**本地開發**

與開發者溝通：
1. 舊 PATs 將在遷移日停止運作
2. 從他們的 Managed User 帳號建立新 PATs
3. 更新 Git Credential Helpers：`git credential reject`
4. 重新驗證 IDE 外掛

### 步驟 7：驗證並撤銷

遷移後，驗證新 Tokens 運作且舊 Tokens 已被撤銷：

```bash
# Test new token
curl -H "Authorization: token NEW_TOKEN" \
  https://api.github.com/user

# Verify access to expected resources
curl -H "Authorization: token NEW_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/test-repo

# Old tokens should fail with 401
curl -H "Authorization: token OLD_TOKEN" \
  https://api.github.com/user
# Expected: {"message":"Bad credentials"...}
```

### Token 遷移檢查清單

| 任務 | 負責人 | 狀態 |
|------|--------|------|
| 完成 Token 盤點 | | ☐ |
| 依遷移路徑分類所有 Tokens | | ☐ |
| 為自動化建立 GitHub Apps | | ☐ |
| 在 EMU 企業中安裝 GitHub Apps | | ☐ |
| 在 IdP 中佈建 Machine Users | | ☐ |
| 為 Machine Users 建立 PATs | | ☐ |
| 將新 Tokens 儲存在密鑰管理工具中 | | ☐ |
| 更新 CI/CD Pipelines | | ☐ |
| 更新外部系統設定 | | ☐ |
| 通知開發者重新建立 PATs | | ☐ |
| 使用新 Tokens 測試所有整合 | | ☐ |
| 記錄 Token 輪換程序 | | ☐ |
| 排程 Token 到期提醒 | | ☐ |
| 驗證舊 Tokens 不再運作 | | ☐ |

## GitHub App 遷移

安裝在舊環境中的 GitHub Apps 不會自動轉移到 EMU。你需要在新企業中重新安裝它們。本節涵蓋完整的遷移流程。

### GitHub Apps 的類型

了解不同類型有助於規劃遷移：

| 類型 | 描述 | 遷移方式 |
|------|------|----------|
| **Marketplace Apps** | 來自 GitHub Marketplace 的第三方 Apps | 從 Marketplace 重新安裝 |
| **Organization Apps** | 由你的組織建立的 Apps | 重新建立或轉移擁有權 |
| **Private Apps** | 未發布的內部 Apps | 在新企業中重新建立 |

### 步驟 1：盤點已安裝的 Apps

列出所有組織中的 GitHub Apps：

```bash
# List installed apps for an organization
gh api orgs/YOUR_ORG/installations \
  --jq '.installations[] | {
    app_slug: .app_slug,
    app_id: .app_id,
    id: .id,
    repository_selection: .repository_selection,
    permissions: .permissions
  }' > installed_apps.json

# For each app, document:
# - App name and purpose
# - Current permissions
# - Repository access (all or selected)
# - Who owns/manages the app
# - EMU compatibility status
```

**建立 App 盤點試算表**

| App 名稱 | 類型 | 用途 | 權限 | 儲存庫存取 | 擁有者 | EMU 相容 | 遷移狀態 |
|----------|------|------|------|-----------|--------|----------|----------|
| Jira | Marketplace | Issue 追蹤 | issues:write, pull_requests:read | 全部 | @devops | ✅ 是 | ☐ 待處理 |
| Dependabot | GitHub | 安全更新 | contents:write, pull_requests:write | 全部 | GitHub | ✅ 是 | ☐ 待處理 |
| Custom Deploy Bot | 內部 | 部署自動化 | contents:write, deployments:write | 選定 | @platform | 需測試 | ☐ 待處理 |
| Legacy Webhook App | 內部 | 通知 | metadata:read | 全部 | 未知 | ❓ 未知 | ☐ 調查中 |

### 步驟 2：檢查 EMU 相容性

並非所有 Apps 都能與 EMU 搭配使用。與供應商確認或在沙箱中測試：

**常見相容性問題**

- **使用者層級 OAuth**：以使用者身分進行驗證的 Apps 可能功能有限
- **公開儲存庫功能**：與公開儲存庫互動的 Apps 不會運作
- **跨企業存取**：Apps 無法存取企業外的資源
- **使用者個人資料存取**：對 Managed User 個人資料資訊的存取有限

**供應商相容性確認範本**

聯繫供應商時，請詢問：

1. 你的 App 是否支援使用 EMU 的 GitHub Enterprise Cloud？
2. 使用 Managed Users 是否有功能限制？
3. EMU 是否需要不同的安裝流程？
4. 是否需要設定變更？
5. 需要哪些權限，它們是否與 EMU 相容？

### 步驟 3：遷移 Marketplace Apps

對於來自 GitHub Marketplace 的 Apps：

1. 在 Marketplace 列表或供應商文件中**驗證 EMU 支援**
2. **在新企業中安裝**：Enterprise Settings → GitHub Apps → Install from Marketplace
3. **設定 App 設定**：套用與原始安裝相同的設定
4. **授予儲存庫存取**：選擇儲存庫或授予組織級存取
5. **測試功能**：驗證 App 是否按預期運作

```bash
# After installation, verify the app is installed
gh api orgs/YOUR_ORG/installations \
  --jq '.installations[] | select(.app_slug == "APP_NAME")'
```

### 步驟 4：重新建立內部/私有 Apps

對於你組織建立的 Apps：

**選項 A：在 EMU 企業中建立新 App**

如果你有原始碼且可以重新建立 App：

1. **匯出目前 App 設定**
   ```bash
   # Document current app settings
   gh api apps/YOUR_APP_SLUG \
     --jq '{
       name: .name,
       description: .description,
       permissions: .permissions,
       events: .events
     }' > app_config.json
   ```

2. **在 EMU 企業中建立新 App**
   - 導覽至 Enterprise Settings → GitHub Apps → New GitHub App
   - 套用已儲存的設定
   - 產生新的 Private Key
   - 記下新的 App ID 和 Installation ID

3. **使用新憑證更新 App 程式碼**
   ```bash
   # Update environment variables or config
   export GITHUB_APP_ID="new_app_id"
   export GITHUB_APP_INSTALLATION_ID="new_installation_id"
   # Replace private key file
   ```

4. **在組織中安裝**
   ```bash
   # Install app in your EMU organizations
   # Via UI: Organization Settings → GitHub Apps → Install
   ```

5. **徹底測試**
   - 驗證 Webhook 傳遞
   - 測試所有 API 操作
   - 確認權限是否足夠

**選項 B：轉移 App 擁有權（如果支援）**

在某些情況下，你可以轉移 App 擁有權：

1. 目前擁有者必須發起轉移
2. 新擁有者（EMU 企業管理員）接受
3. 轉移後更新安裝設定
4. 為安全性重新產生 Private Keys

> **注意：** App 轉移很複雜，可能不會保留所有設定。重新建立通常更乾淨。

### 步驟 5：處理 Webhooks

Apps 常依賴 Webhooks。這些需要重新設定：

```bash
# List current webhooks
gh api orgs/YOUR_ORG/hooks \
  --jq '.[] | {
    id: .id,
    name: .name,
    active: .active,
    url: .config.url,
    events: .events
  }'

# After migration, recreate webhooks with new secrets
gh api orgs/NEW_ORG/hooks \
  -X POST \
  -f name='web' \
  -f active=true \
  -f events[]='push' \
  -f events[]='pull_request' \
  -f config[url]='https://your-webhook-endpoint.com/github' \
  -f config[content_type]='json' \
  -f config[secret]='NEW_WEBHOOK_SECRET'
```

**Webhook 遷移檢查清單**

| Webhook URL | 事件 | 目前 Secret 位置 | 新 Secret 已建立 | 已測試 |
|-------------|------|-----------------|-----------------|--------|
| https://jenkins.internal/github | push, pr | Jenkins Credentials | ☐ | ☐ |
| https://slack.com/webhook/xxx | push, issues | Slack App Config | ☐ | ☐ |

### 步驟 6：更新 App 身分驗證

重新建立 Apps 後，更新所有進行驗證的地方：

**GitHub Actions Workflows**

```yaml
# Update App ID and private key references
- uses: actions/create-github-app-token@v1
  with:
    app-id: ${{ vars.NEW_APP_ID }}  # Updated
    private-key: ${{ secrets.NEW_APP_PRIVATE_KEY }}  # New key
```

**外部服務**

| 服務 | 設定位置 | 需更新的值 |
|------|----------|-----------|
| Jenkins | Manage Jenkins → Credentials | App ID、Private Key、Installation ID |
| ArgoCD | argocd-cm ConfigMap | GitHub App 憑證 |
| Backstage | app-config.yaml | integrations.github 區段 |
| 自訂服務 | 環境變數 | 所有 GitHub App 憑證 |

### 步驟 7：驗證 App 功能

為每個遷移的 App 建立測試計畫：

```markdown
## App 遷移測試計畫：[App 名稱]

### 遷移前基準
- [ ] 記錄目前 App 行為
- [ ] 擷取範例 Webhook Payloads
- [ ] 記下 API 回應格式

### 遷移後測試
- [ ] App 安裝在組織設定中可見
- [ ] Webhook 傳遞成功（檢查 App Settings → Advanced）
- [ ] API 身分驗證運作
- [ ] 所有預期權限已授予
- [ ] 儲存庫存取正確（全部 vs. 選定）
- [ ] 事件訂閱正確觸發

### 功能測試
- [ ] [測試特定功能 1]
- [ ] [測試特定功能 2]
- [ ] [測試錯誤處理]

### 回退計畫
- [ ] 記錄如發現問題如何還原
- [ ] 識別關鍵路徑依賴
```

### GitHub App 遷移檢查清單

| 任務 | 負責人 | 狀態 |
|------|--------|------|
| 盤點所有已安裝的 GitHub Apps | | ☐ |
| 記錄 App 用途和擁有者 | | ☐ |
| 驗證每個 App 的 EMU 相容性 | | ☐ |
| 聯繫不相容 Apps 的供應商 | | ☐ |
| 重新安裝 Marketplace Apps | | ☐ |
| 重新建立內部 Apps | | ☐ |
| 產生新的 Private Keys | | ☐ |
| 更新 Webhook 設定 | | ☐ |
| 輪換 Webhook Secrets | | ☐ |
| 使用新 App 憑證更新 CI/CD | | ☐ |
| 更新外部服務 | | ☐ |
| 測試所有 App 功能 | | ☐ |
| 停用舊的 App 安裝 | | ☐ |
| 記錄新的 App IDs 和 Installation IDs | | ☐ |

## Artifact 管理和 GitHub Packages

GitHub Packages 可與 EMU 搭配使用，但對於你的 Artifact 管理策略有一些重要考量。

### 支援的 Package 類型

EMU 中的 GitHub Packages 支援：
- **Container Registry** (ghcr.io)：Docker 和 OCI Images
- **npm**：JavaScript Packages
- **Maven**：Java Packages
- **NuGet**：.NET Packages
- **RubyGems**：Ruby Packages

### 身分驗證變更

Managed Users 以相同方式對 GitHub Packages 進行身分驗證，但使用企業範圍的 Tokens：

```bash
# Docker login with PAT
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME_shortcode --password-stdin

# npm configuration
npm login --registry=https://npm.pkg.github.com --scope=@your-org

# Maven settings.xml
<server>
  <id>github</id>
  <username>USERNAME_shortcode</username>
  <password>${GITHUB_TOKEN}</password>
</server>
```

### Package 可見性和存取

在 EMU 企業中：
- **沒有公開 Packages**：所有 Packages 都是 Private 或 Internal（在企業內可見）
- **組織範圍**：Packages 屬於組織，而非個人帳號
- **權限繼承**：Package 存取遵循儲存庫權限

### 遷移注意事項

遷移現有 Packages 時：

1. **盤點現有 Packages**：列出所有 Registries 中的 Packages
2. **規劃命名空間變更**：Package URLs 會隨新組織結構而改變
3. **更新 CI/CD Pipelines**：修改發布/拉取設定
4. **通知使用者**：內部團隊需要新的 Registry URLs
5. **考慮快取**：設定 Artifact 快取以提升建置效能

```yaml
# Example: Updated workflow for EMU package publishing
name: Publish Package
on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

### 外部 Registry 整合

如果你使用外部 Registries（Artifactory、Nexus、ECR、ACR），它們將繼續運作：
- 在 GitHub Actions Secrets 中設定身分驗證
- 盡可能使用 OIDC 用於雲端供應商 Registries
- 更新對 GitHub Packages URLs 的任何引用

## Code Security 和 GitHub Advanced Security

EMU 企業可以充分利用 GitHub Advanced Security (GHAS) 功能。以下是如何最大化你的安全態勢。

### GitHub Advanced Security 功能

**Code Scanning**
- 對你的程式碼庫執行 CodeQL 分析
- 識別安全漏洞和程式碼錯誤
- 與 PR Workflow 整合以實現左移安全
- 支援針對組織特定模式的自訂查詢

```yaml
# Enable code scanning in your workflow
name: "CodeQL"
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly scan

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript, python
      - uses: github/codeql-action/analyze@v3
```

**Secret Scanning**
- 偵測意外提交到儲存庫的密鑰
- 支援來自合作夥伴的 200 多種密鑰模式
- 支援組織特定密鑰的自訂模式
- Push Protection 在密鑰提交前阻止它們

**Dependabot**
- 自動化依賴更新
- 安全漏洞警報
- 版本更新以保持依賴為最新
- 在 EMU 企業邊界內運作

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
```

### Enterprise 安全設定

大規模設定安全功能：

```
Enterprise Settings → Code security and analysis
```

**建議設定：**
- ✅ 為所有儲存庫啟用 Dependabot Alerts
- ✅ 為所有儲存庫啟用 Dependabot Security Updates
- ✅ 為所有儲存庫啟用 Secret Scanning
- ✅ 為所有儲存庫啟用 Push Protection
- ✅ 為所有儲存庫啟用 Code Scanning Default Setup

### Security Overview Dashboard

EMU 企業可以存取 Security Overview Dashboard：
- 所有組織的企業級安全警報檢視
- 跨所有組織的風險評估
- 安全功能的覆蓋率指標
- 警報趨勢隨時間變化

請參閱 [About the security overview](https://docs.github.com/en/code-security/security-overview/about-the-security-overview)。

### Private Vulnerability Reporting

啟用 Private Vulnerability Reporting 以允許安全研究人員秘密報告問題：

```
Repository Settings → Security → Private vulnerability reporting
```

這為漏洞揭露建立了安全管道，無需公開曝光。

### 安全政策

在你的 `.github` 儲存庫中建立 `SECURITY.md` 檔案以制定組織級安全政策：

```markdown
# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities through our private vulnerability reporting feature
or by emailing security@company.com.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |
```

---

> **📚 EMU 遷移指南系列導覽**
>
> ⬅️ **上一篇：[第 3 部分 - 身分識別與存取設定](Part3-Identity&Access%20Setup.md)**
> ➡️ **下一篇：[第 5 部分 - 遷移執行](Part5-MigrationExecution.md)**
>
> ---
> *這是遷移至 GitHub Enterprise Managed Users 六部分系列的第 4 部分。覺得有幫助？給個 👍 並與你的團隊分享！有問題或我遺漏了什麼？請在下方留言。*
