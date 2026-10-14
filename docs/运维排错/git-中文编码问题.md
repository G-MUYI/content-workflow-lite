# Git / GitHub 中文目录名显示为转义序列

> 记录时间：2026-02-27

## 现象

GitHub 仓库页面上，中文目录名显示为八进制转义序列：
```
"\346\225\260\346\215\256\347\273\237\350\256\241"  ← 实际是「数据统计」
"\347\264\240\346\235\220\345\272\223"              ← 实际是「素材库」
"\351\200\211\351\242\230\345\272\223"              ← 实际是「选题库」
```

## 原因

1. Git 默认 `core.quotepath=true`，会对非 ASCII 字符做八进制转义显示
2. 某些情况下，特定 commit 的 tree 对象在推送到 GitHub 后被错误解析，导致 GitHub 网页端也显示转义序列
3. 本地 `git cat-file tree` 的原始字节是正确的 UTF-8，问题出在 GitHub 对该 tree SHA 的解析

## 排查方法

```bash
# 1. 检查本地显示
git config --get core.quotepath

# 2. 通过 GitHub API 检查远程 tree
gh api repos/:owner/:repo/git/trees/HEAD --jq '.tree[].path'

# 3. 逐个 commit 对比，定位是哪个 commit 的 tree 出问题
gh api repos/:owner/:repo/git/trees/<commit-sha> --jq '.tree[].path'
```

## 解决方法

### 本地显示修复
```bash
git config --global core.quotepath false
```

### GitHub 显示修复
创建一个新提交（改动任意文件），生成新的 root tree SHA，推送后 GitHub 会重新解析：
```bash
# 在中文目录下的任意文件做一个小改动
git add <file>
git commit -m "fix: 修复 GitHub 中文目录名显示"
git push
```
关键原理：新 commit 产生新的 tree SHA → GitHub 为新 tree 创建新的解析记录 → 中文正常显示。
