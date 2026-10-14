# Nano Banana Pro Component Library

> **Usage**: Mix and match these components to assemble a complete HTML card. Do not alter the class names unless necessary for content fit.

---

## 1. Base Layouts

### 1.1 Root Container (The Canvas)
> Fixed width 600px, responsive height. Always the outer wrapper.

```html
<div class="card-container w-[600px] min-h-[800px] p-8 flex items-center justify-center relative overflow-hidden bg-gradient-to-br from-blue-50 via-indigo-50 to-white font-sans text-slate-800">
  <!-- Glowing Orbs Background -->
  <div class="absolute top-[-10%] left-[-10%] w-[300px] h-[300px] bg-blue-200 rounded-full mix-blend-multiply filter blur-[80px] opacity-40 animate-blob"></div>
  <div class="absolute bottom-[-10%] right-[-10%] w-[300px] h-[300px] bg-indigo-200 rounded-full mix-blend-multiply filter blur-[80px] opacity-40 animate-blob animation-delay-2000"></div>

  <!-- Inner White Card -->
  <div class="bg-white/90 backdrop-blur-xl w-full h-full min-h-[740px] rounded-[32px] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] border border-white/50 flex flex-col relative z-10 overflow-hidden">
    <!-- CONTENT GOES HERE -->
  </div>
</div>
```

---

## 2. Color Themes (Palette)

Apply these gradients to the `card-container` `bg-gradient-to-br` section.

| Theme | Gradient Classes | Accent Color |
|-------|------------------|--------------|
| **Tech/Cool** | `from-blue-50 via-indigo-50 to-white` | `indigo` |
| **Warm/Life** | `from-rose-50 via-pink-50 to-white` | `rose` |
| **Biz/Pro** | `from-slate-100 via-gray-50 to-white` | `slate` |
| **Nature** | `from-emerald-50 via-teal-50 to-white` | `teal` |
| **Luxe/Gold** | `from-stone-100 via-orange-50 to-white` | `amber` |
| **Pop/Vibrant** | `from-violet-100 via-fuchsia-100 to-yellow-50` | `violet` |

### Full Theme Token Map

> 生成器 `generate-nano.js` 中的 `THEMES` 对象与此表一一对应。AI 在 JSON 中设置 `theme.style` 为以下 key 之一即可。

| Token | `tech` | `life` | `business` | `nature` | `luxe` | `pop` |
|-------|--------|--------|------------|----------|--------|-------|
| gradient | `from-blue-50 via-indigo-50 to-white` | `from-rose-50 via-pink-50 to-white` | `from-slate-100 via-gray-50 to-white` | `from-emerald-50 via-teal-50 to-white` | `from-stone-100 via-orange-50 to-white` | `from-violet-100 via-fuchsia-100 to-yellow-50` |
| accent | `indigo` | `rose` | `slate` | `teal` | `amber` | `violet` |
| innerCard style | Glassmorphism | Soft UI | Standard | Standard | Luxury/Minimal | Neubrutalism |

---

## 2.5. Design Styles (Visual DNA)

Apply these classes to the **Inner White Card** (`bg-white/90...`) to change its feel.

| Style | Classes Override |
|-------|-----------------|
| **Standard (Nano)** | `bg-white/90 backdrop-blur-xl border border-white/50 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] rounded-[32px]` |
| **Glassmorphism** | `bg-white/40 backdrop-blur-2xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.15)] rounded-[32px]` |
| **Soft UI (Neumorphism)** | `bg-[#efeeee] shadow-[20px_20px_60px_#cbced1,-20px_-20px_60px_#ffffff] border-none rounded-[40px]` (Requires lighter bg) |
| **Neubrutalism** | `bg-white border-4 border-slate-900 shadow-[8px_8px_0px_0px_rgba(15,23,42,1)] rounded-none` |
| **Luxury / Minimal** | `bg-white border border-stone-200 shadow-none rounded-none` |

> **Theme <-> Style 推荐映射**：`tech` -> Glassmorphism, `life` -> Soft UI, `business` -> Standard, `nature` -> Standard, `luxe` -> Luxury/Minimal, `pop` -> Neubrutalism

---

## 3. Header Components

### 3.1 Standard Header (Topic + Index)

```html
<div class="p-8 pb-4 flex justify-between items-start">
  <div>
    <span class="text-indigo-500 font-bold text-xs tracking-[0.2em] uppercase mb-2 block">TOPIC</span>
    <h2 class="font-sans text-3xl font-bold text-slate-900 leading-tight">Card Title Here</h2>
  </div>
  <div class="w-12 h-12 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 font-bold font-sans text-xl border border-indigo-100">
    01
  </div>
</div>
```

### 3.2 Cover Title — Top-Bottom Layout (Big & Bold + Preview List)

> 上下引导构图：上方大标题 + 下方内容预览列表。适合有 3+ 要点的内容。`layout: "top-bottom"`（默认）

```html
<div class="p-10 flex-1 flex flex-col justify-between relative z-20">
  <div>
    <span class="inline-block px-3 py-1 rounded-full bg-orange-100/80 text-orange-600 text-xs font-bold tracking-wider uppercase mb-6 backdrop-blur-sm">
      KEYWORD
    </span>
    <h1 class="font-sans text-5xl font-bold text-slate-900 leading-[1.1] mb-4">
      Main Title<br/>
      <span class="text-indigo-500">Highlight Part</span>
    </h1>
  </div>
  <div class="space-y-6 mt-10">
    <!-- Preview points from content cards -->
  </div>
  <div class="mt-auto pt-10 flex justify-between items-end border-t border-gray-100">
    <span class="text-[10px] font-bold tracking-widest uppercase opacity-40">@USERNAME</span>
    <span class="text-[10px] font-sans italic opacity-40">Nano Series</span>
  </div>
</div>
```

### 3.3 Cover Title — Center Focus Layout

> 居中聚焦构图：标题大字居中，装饰分割线，大量留白，高级感。适合单一核心概念、金句型内容。`layout: "center"`

```html
<div class="p-12 flex flex-col h-full justify-center text-center relative z-20">
  <span class="inline-block px-3 py-1 rounded-full bg-orange-100/80 text-orange-600 text-xs font-bold tracking-wider uppercase mb-10 mx-auto backdrop-blur-sm">
    KEYWORD
  </span>
  <h1 class="font-sans text-6xl font-bold text-slate-900 leading-[1.05] mb-8 px-4">
    Main Title Here
  </h1>
  <div class="w-16 h-1 bg-indigo-400 mx-auto rounded-full mb-8 opacity-60"></div>
  <p class="text-slate-400 text-base font-light tracking-widest uppercase px-12">
    A short subtitle or visual hook
  </p>
  <div class="mt-auto pt-10 flex justify-between items-end opacity-40">
    <span class="text-[10px] font-bold tracking-widest uppercase">@USERNAME</span>
    <span class="text-[10px] font-sans italic">Nano Series</span>
  </div>
</div>
```

### 3.4 Cover Title — Big Number Layout

> 数字主导构图：超大数字 + 幽灵数字背景层叠，强烈视觉冲击。适合数据驱动、数字冲击力的内容。`layout: "big-number"`

```html
<div class="p-10 flex flex-col h-full justify-center relative z-20">
  <span class="inline-block px-3 py-1 rounded-full bg-orange-100/80 text-orange-600 text-xs font-bold tracking-wider uppercase mb-8 backdrop-blur-sm w-fit">
    KEYWORD
  </span>
  <div class="relative mb-6">
    <div class="absolute -top-4 -left-2 text-[160px] font-bold text-indigo-500 opacity-[0.07] font-sans leading-none select-none pointer-events-none">3000</div>
    <div class="text-8xl font-bold text-indigo-500 font-sans leading-none relative">3000</div>
  </div>
  <div class="w-12 h-1 bg-indigo-400 rounded-full mb-5"></div>
  <h1 class="font-sans text-2xl font-bold text-slate-900 leading-tight mb-3">
    Main Title Here
  </h1>
  <p class="text-slate-400 text-sm font-light tracking-wide">
    A short subtitle or description
  </p>
  <div class="mt-auto pt-10 flex justify-between items-end opacity-40">
    <span class="text-[10px] font-bold tracking-widest uppercase">@USERNAME</span>
    <span class="text-[10px] font-sans italic">Nano Series</span>
  </div>
</div>
```

---

## 4. Content Blocks

### 4.1 Concept Pill (Pain Point / Solution)

> 对应 JSON `type: "观点块"`

```html
<div class="px-8 mb-6">
  <div class="bg-indigo-50/50 rounded-2xl p-5 border border-indigo-50">
    <div class="flex gap-3 mb-2 items-start">
      <span class="flex-shrink-0 px-2 py-0.5 rounded bg-red-100 text-red-600 text-[10px] font-bold uppercase tracking-wide mt-0.5">Pain</span>
      <p class="text-sm text-slate-600 leading-relaxed">
        Why process is currently broken or difficult.
      </p>
    </div>
    <div class="flex gap-3 items-start">
      <span class="flex-shrink-0 px-2 py-0.5 rounded bg-emerald-100 text-emerald-600 text-[10px] font-bold uppercase tracking-wide mt-0.5">Fix</span>
      <p class="text-sm text-slate-800 font-medium leading-relaxed">
        The better way to do it using this method.
      </p>
    </div>
  </div>
</div>
```

### 4.2 Code Window (Mac Style)

> 对应 JSON `type: "代码块"`

```html
<div class="px-8 mt-auto mb-8">
  <div class="bg-slate-900 rounded-2xl p-5 shadow-2xl relative group overflow-hidden">
    <!-- Window Controls -->
    <div class="flex gap-1.5 mb-4 opacity-50">
      <div class="w-2.5 h-2.5 rounded-full bg-red-500"></div>
      <div class="w-2.5 h-2.5 rounded-full bg-yellow-500"></div>
      <div class="w-2.5 h-2.5 rounded-full bg-green-500"></div>
    </div>
    <!-- Code Content -->
    <code class="block font-mono text-xs text-blue-200 leading-relaxed whitespace-pre font-light">
const <span class="text-yellow-300">magic</span> = () => {
  return "This looks premium";
}
    </code>
    <!-- Copy Tag -->
    <div class="absolute top-4 right-4 text-[10px] text-slate-500 font-mono tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">COPIED</div>
  </div>
</div>
```

### 4.3 Checklist

> 对应 JSON `type: "清单块"`

```html
<div class="px-8 space-y-3 mb-8">
  <!-- Item -->
  <div class="flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-100 shadow-sm">
    <div class="w-5 h-5 rounded-full border-2 border-indigo-400 flex items-center justify-center">
      <div class="w-2.5 h-2.5 rounded-full bg-indigo-400"></div>
    </div>
    <span class="text-slate-700 text-sm font-medium">Identify the core problem</span>
  </div>
  <!-- Item -->
  <div class="flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-100 shadow-sm opacity-60">
    <div class="w-5 h-5 rounded-full border-2 border-slate-300"></div>
    <span class="text-slate-500 text-sm">Automate the solution</span>
  </div>
</div>
```

### 4.4 Glass Note

> 对应 JSON `type: "金句块"`

```html
<div class="mx-8 p-6 rounded-2xl bg-indigo-600/5 border border-indigo-600/10 text-center relative">
   <span class="absolute -top-3 left-1/2 -translate-x-1/2 bg-white px-2 py-0.5 text-[10px] font-bold text-indigo-400 tracking-widest uppercase shadow-sm rounded-full border border-indigo-50">Note</span>
   <p class="text-indigo-900 text-sm italic font-medium leading-relaxed">
     "Simplicity is the ultimate sophistication."
   </p>
</div>
```

### 4.5 Stat Card (Data Display)

> 对应 JSON `type: "数据块"`。支持 1~3 个数据项并排展示。

```html
<div class="px-8 mb-6">
  <div class="flex gap-4">
    <!-- Single Stat Item -->
    <div class="flex-1 bg-indigo-50/50 rounded-2xl p-5 border border-indigo-50 text-center">
      <div class="text-4xl font-bold text-indigo-600 font-sans leading-none mb-2">3000+</div>
      <div class="text-xs text-slate-500 font-medium tracking-wide uppercase">Users</div>
    </div>
    <!-- Add more items as needed, up to 3 -->
  </div>
</div>
```

### 4.6 VS Card (Before/After Comparison)

> 对应 JSON `type: "对比块"`。左右两栏对比，左侧旧方式 / 右侧新方式。

```html
<div class="px-8 mb-6">
  <div class="grid grid-cols-2 gap-3">
    <!-- Before -->
    <div class="bg-red-50/50 rounded-2xl p-4 border border-red-100">
      <div class="flex items-center gap-2 mb-3">
        <span class="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center text-red-500 text-xs font-bold">✕</span>
        <span class="text-xs font-bold text-red-500 uppercase tracking-wide">Before</span>
      </div>
      <p class="text-sm text-slate-600 leading-relaxed">The old way of doing things that causes problems.</p>
    </div>
    <!-- After -->
    <div class="bg-emerald-50/50 rounded-2xl p-4 border border-emerald-100">
      <div class="flex items-center gap-2 mb-3">
        <span class="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-500 text-xs font-bold">✓</span>
        <span class="text-xs font-bold text-emerald-500 uppercase tracking-wide">After</span>
      </div>
      <p class="text-sm text-slate-800 font-medium leading-relaxed">The better approach that solves the problem.</p>
    </div>
  </div>
</div>
```

### 4.7 Step Flow (Ordered Steps)

> 对应 JSON `type: "步骤块"`。带序号的垂直步骤流，连线连接。

```html
<div class="px-8 mb-6">
  <div class="space-y-0">
    <!-- Step Item -->
    <div class="flex gap-4 items-start">
      <div class="flex flex-col items-center">
        <div class="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">1</div>
        <div class="w-0.5 h-8 bg-indigo-200"></div>
      </div>
      <div class="pt-1 pb-4">
        <p class="text-sm text-slate-700 font-medium leading-relaxed">First step description here</p>
      </div>
    </div>
    <!-- Step Item (last, no connector line) -->
    <div class="flex gap-4 items-start">
      <div class="flex flex-col items-center">
        <div class="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">2</div>
      </div>
      <div class="pt-1">
        <p class="text-sm text-slate-700 font-medium leading-relaxed">Last step description here</p>
      </div>
    </div>
  </div>
</div>
```

### 4.8 Highlight Box (Key Takeaway)

> 对应 JSON `type: "高亮块"`。带左侧强调色条的高亮框，用于核心结论。

```html
<div class="px-8 mb-6">
  <div class="bg-indigo-50/30 rounded-2xl p-5 border-l-4 border-indigo-500">
    <p class="text-sm text-slate-800 font-medium leading-relaxed">
      Core conclusion or key takeaway text goes here. This is the most important thing to remember.
    </p>
  </div>
</div>
```

### 4.9 Image Block (Screenshot / Image Embed)

> 对应 JSON `type: "图片块"`。嵌入截图或图片，支持本地文件路径和 URL。可设为占位符模式。

**有图片时**：
```html
<div class="px-8 mb-6">
  <div class="rounded-2xl overflow-hidden border border-indigo-50 shadow-sm">
    <img src="path/to/image.png" alt="caption" class="w-full h-auto object-cover" style="max-height: 400px;" />
  </div>
  <p class="text-xs text-slate-400 text-center mt-3 font-medium tracking-wide">图片说明文字</p>
</div>
```

**占位符模式**（仅中间草案；先复用或获取已授权截图，关键图未补齐不能报告成品完成）：
```html
<div class="px-8 mb-6">
  <div class="rounded-2xl overflow-hidden border-2 border-dashed border-indigo-50 bg-indigo-50/50 flex items-center justify-center" style="min-height: 200px;">
    <div class="text-center p-6">
      <div class="text-3xl mb-3 opacity-30">📷</div>
      <p class="text-sm text-indigo-500 font-medium">这里需要一张操作界面的截图</p>
    </div>
  </div>
</div>
```

---

## 5. Footer Components

### 5.1 Simple Footer

```html
<div class="mt-auto p-8 pt-0 flex justify-between items-center opacity-40">
  <span class="text-[10px] font-bold tracking-widest uppercase">@USERNAME</span>
  <span class="text-[10px] font-sans italic">Nano Series</span>
</div>
```
