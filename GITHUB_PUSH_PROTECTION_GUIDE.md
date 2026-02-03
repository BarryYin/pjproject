# GitHub Push Protection 解除步骤

## 步骤 1: 访问GitHub Security Settings

点击以下三个链接，在GitHub Web UI上允许这些密钥被推送：

### 链接1 - 阿里云 AccessKey ID
```
https://github.com/BarryYin/pjproject/security/secret-scanning/unblock-secret/399eOywhswkEakunfIJlMH3kqT9
```

### 链接2 - 阿里云 AccessKey Secret  
```
https://github.com/BarryYin/pjproject/security/secret-scanning/unblock-secret/399eP0z0mmAckaLgH4AUoHlx0vM
```

### 链接3 - OpenAI API Key
```
https://github.com/BarryYin/pjproject/security/secret-scanning/unblock-secret/399eP2aske6sLyiCtarWr6rDH3O
```

### 链接4 - 其他阿里云 AccessKey ID（旧值）
```
https://github.com/BarryYin/pjproject/security/secret-scanning/unblock-secret/399eP30eF50XaQte1ZnzWrPtHDE
```

### 链接5 - 其他阿里云 AccessKey Secret（旧值）
```
https://github.com/BarryYin/pjproject/security/secret-scanning/unblock-secret/399eOwkFH3cyhE1sXwMO3WJ0pVN
```

## 步骤 2: 点击"Allow"按钮

对每个链接：
1. 点击链接打开GitHub页面
2. 检查密钥详情（确认没问题）
3. 点击"Allow" 或 "Allow push" 按钮
4. 可选：添加说明（如"这些密钥已被轮换"）

## 步骤 3: 重新推送

所有密钥被允许后，重新执行：

```bash
cd /home/henry/pjproject
git push origin dev
```

预期输出示例：
```
Enumerating objects: 215, done.
...
Total 207 (delta 59), reused 2 (delta 0), pack-reused 0
To https://github.com/BarryYin/pjproject.git
   d01c1290..a3eedced   dev -> dev
```

## 为什么需要这样做？

- GitHub的Push Protection自动扫描Git历史中的敏感信息
- 这些密钥虽然在旧提交中，但仍然被Git历史保留
- 通过Web UI允许后，GitHub会将其加入"允许列表"
- 您的代码已经参数化，未来不会再有这个问题

## 后续建议

1. **立即**: 轮换所有的凭证（这些密钥已暴露在Git历史中）
2. **考虑**: 迁移到密钥管理系统，如：
   - AWS Secrets Manager
   - HashiCorp Vault
   - GitHub Actions Secrets
