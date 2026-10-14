# 小红书卡片生成器 (Nano Component Edition)

基于组件库的小红书卡片图片生成器。支持 6 种视觉主题。

## 安装依赖

首次使用前，安装 Puppeteer：

```bash
# 方式一：使用安装脚本
setup.bat

# 方式二：手动安装
npm install
```

## 使用方法

```bash
node generate-nano.js <data.json> [output-dir]
```

- `data.json`：卡片数据文件（参考 `example-data.json`）
- `output-dir`：可选，输出目录。默认输出到 data.json 同级目录

### 示例

```bash
# 基本用法（输出到 data.json 同级目录）
node generate-nano.js example-data.json

# 指定输出目录
node generate-nano.js data.json ./output
```

## 文件说明

- `generate-nano.js`：核心生成逻辑（Node.js + Puppeteer）
- `example-data.json`：示例数据
- `setup.bat`：依赖安装脚本
- `package.json`：项目配置

## 支持的主题

| 主题 | 风格 | 适用内容 |
|------|------|---------|
| `tech` | Glassmorphism | 技术/AI/代码 |
| `life` | Soft UI | 生活/感悟/故事 |
| `business` | Minimalism | 商业/赚钱/效率 |
| `nature` | Organic | 自然/健康/治愈 |
| `luxe` | Luxury/Minimal | 高端/奢侈/美学 |
| `pop` | Neubrutalism | 年轻/潮流/搞怪 |
