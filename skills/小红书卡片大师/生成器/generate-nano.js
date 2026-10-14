/**
 * 小红书卡片生成器 v3.0 (Nano Component Edition)
 *
 * 基于 components-library.md 组件库，通过组件拼装生成高质量视觉卡片。
 * 支持 6 种主题：tech / life / business / nature / luxe / pop
 * 支持 3 种封面构图：top-bottom / center / big-number
 * 支持 10 种内容块：观点块 / 代码块 / 清单块 / 金句块 / 解释块 / 数据块 / 对比块 / 步骤块 / 高亮块 / 图片块
 *
 * 使用方法：
 *   node generate-nano.js <data.json> [output-dir]
 */

const fs = require('fs').promises;
const path = require('path');
const puppeteer = require('puppeteer');

// ============================================================
// 1. Theme Definitions (6 themes, matching components-library.md)
// ============================================================
const THEMES = {
    tech: {
        gradient: 'from-blue-50 via-indigo-50 to-white',
        topicText: 'text-indigo-500',
        indexBg: 'bg-indigo-50',
        indexText: 'text-indigo-600',
        indexBorder: 'border-indigo-100',
        coverTagBg: 'bg-indigo-100/80',
        coverTagText: 'text-indigo-600',
        highlightText: 'text-indigo-500',
        conceptBg: 'bg-indigo-50/50',
        conceptBorder: 'border-indigo-50',
        painBadgeBg: 'bg-red-100',
        painBadgeText: 'text-red-600',
        solBadgeBg: 'bg-emerald-100',
        solBadgeText: 'text-emerald-600',
        glassNoteBg: 'bg-indigo-600/5',
        glassNoteBorder: 'border-indigo-600/10',
        glassNoteLabel: 'text-indigo-400',
        glassNoteText: 'text-indigo-900',
        checkBorder: 'border-indigo-400',
        checkFill: 'bg-indigo-400',
        orbColor1: 'bg-blue-300',
        orbColor2: 'bg-indigo-300',
        innerCard: 'bg-white/40 backdrop-blur-2xl border border-white/60 shadow-[0_8px_32px_0_rgba(31,38,135,0.15)] rounded-[32px]',
    },
    life: {
        gradient: 'from-rose-50 via-pink-50 to-white',
        topicText: 'text-rose-500',
        indexBg: 'bg-rose-50',
        indexText: 'text-rose-600',
        indexBorder: 'border-rose-100',
        coverTagBg: 'bg-rose-100/80',
        coverTagText: 'text-rose-600',
        highlightText: 'text-rose-500',
        conceptBg: 'bg-rose-50/50',
        conceptBorder: 'border-rose-50',
        painBadgeBg: 'bg-orange-100',
        painBadgeText: 'text-orange-500',
        solBadgeBg: 'bg-teal-100',
        solBadgeText: 'text-teal-500',
        glassNoteBg: 'bg-rose-600/5',
        glassNoteBorder: 'border-rose-600/10',
        glassNoteLabel: 'text-rose-400',
        glassNoteText: 'text-rose-900',
        checkBorder: 'border-rose-400',
        checkFill: 'bg-rose-400',
        orbColor1: 'bg-rose-300',
        orbColor2: 'bg-pink-300',
        innerCard: 'bg-[#efeeee] shadow-[20px_20px_60px_#cbced1,-20px_-20px_60px_#ffffff] border-none rounded-[40px]',
    },
    business: {
        gradient: 'from-slate-100 via-gray-50 to-white',
        topicText: 'text-slate-500',
        indexBg: 'bg-slate-100',
        indexText: 'text-slate-700',
        indexBorder: 'border-slate-200',
        coverTagBg: 'bg-slate-200/80',
        coverTagText: 'text-slate-600',
        highlightText: 'text-slate-600',
        conceptBg: 'bg-slate-50/50',
        conceptBorder: 'border-slate-100',
        painBadgeBg: 'bg-red-50',
        painBadgeText: 'text-red-600',
        solBadgeBg: 'bg-emerald-50',
        solBadgeText: 'text-emerald-600',
        glassNoteBg: 'bg-slate-600/5',
        glassNoteBorder: 'border-slate-600/10',
        glassNoteLabel: 'text-slate-400',
        glassNoteText: 'text-slate-900',
        checkBorder: 'border-slate-400',
        checkFill: 'bg-slate-400',
        orbColor1: 'bg-slate-300',
        orbColor2: 'bg-gray-300',
        innerCard: 'bg-white/90 backdrop-blur-xl border border-white/50 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] rounded-[32px]',
    },
    nature: {
        gradient: 'from-emerald-50 via-teal-50 to-white',
        topicText: 'text-teal-500',
        indexBg: 'bg-teal-50',
        indexText: 'text-teal-600',
        indexBorder: 'border-teal-100',
        coverTagBg: 'bg-teal-100/80',
        coverTagText: 'text-teal-600',
        highlightText: 'text-teal-500',
        conceptBg: 'bg-teal-50/50',
        conceptBorder: 'border-teal-50',
        painBadgeBg: 'bg-amber-100',
        painBadgeText: 'text-amber-600',
        solBadgeBg: 'bg-cyan-100',
        solBadgeText: 'text-cyan-600',
        glassNoteBg: 'bg-teal-600/5',
        glassNoteBorder: 'border-teal-600/10',
        glassNoteLabel: 'text-teal-400',
        glassNoteText: 'text-teal-900',
        checkBorder: 'border-teal-400',
        checkFill: 'bg-teal-400',
        orbColor1: 'bg-emerald-300',
        orbColor2: 'bg-teal-300',
        innerCard: 'bg-white/90 backdrop-blur-xl border border-white/50 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] rounded-[32px]',
    },
    luxe: {
        gradient: 'from-stone-100 via-orange-50 to-white',
        topicText: 'text-amber-600',
        indexBg: 'bg-amber-50',
        indexText: 'text-amber-700',
        indexBorder: 'border-amber-100',
        coverTagBg: 'bg-amber-100/80',
        coverTagText: 'text-amber-700',
        highlightText: 'text-amber-600',
        conceptBg: 'bg-amber-50/50',
        conceptBorder: 'border-amber-50',
        painBadgeBg: 'bg-red-50',
        painBadgeText: 'text-red-500',
        solBadgeBg: 'bg-emerald-50',
        solBadgeText: 'text-emerald-600',
        glassNoteBg: 'bg-amber-600/5',
        glassNoteBorder: 'border-amber-600/10',
        glassNoteLabel: 'text-amber-400',
        glassNoteText: 'text-amber-900',
        checkBorder: 'border-amber-400',
        checkFill: 'bg-amber-400',
        orbColor1: 'bg-orange-300',
        orbColor2: 'bg-amber-300',
        innerCard: 'bg-white border border-stone-200 shadow-none rounded-none',
    },
    pop: {
        gradient: 'from-violet-100 via-fuchsia-100 to-yellow-50',
        topicText: 'text-violet-500',
        indexBg: 'bg-violet-100',
        indexText: 'text-violet-600',
        indexBorder: 'border-violet-200',
        coverTagBg: 'bg-violet-100/80',
        coverTagText: 'text-violet-600',
        highlightText: 'text-violet-500',
        conceptBg: 'bg-violet-50/50',
        conceptBorder: 'border-violet-100',
        painBadgeBg: 'bg-pink-100',
        painBadgeText: 'text-pink-600',
        solBadgeBg: 'bg-lime-100',
        solBadgeText: 'text-lime-600',
        glassNoteBg: 'bg-violet-600/5',
        glassNoteBorder: 'border-violet-600/10',
        glassNoteLabel: 'text-violet-400',
        glassNoteText: 'text-violet-900',
        checkBorder: 'border-violet-400',
        checkFill: 'bg-violet-400',
        orbColor1: 'bg-violet-300',
        orbColor2: 'bg-fuchsia-300',
        innerCard: 'bg-white border-4 border-slate-900 shadow-[8px_8px_0px_0px_rgba(15,23,42,1)] rounded-none',
    },
};

// ============================================================
// 2. Theme Selection — directly read data.theme.style
// ============================================================
function getTheme(data) {
    const style = (data.theme?.style || '').toLowerCase();
    if (THEMES[style]) return style;
    return 'tech';
}

// ============================================================
// 3. Component Renderers (matching components-library.md)
// ============================================================

/** Root Container — wraps every card */
function renderRootContainer(innerHtml, theme) {
    return `
    <div class="card-container w-[600px] min-h-[800px] p-8 flex items-center justify-center relative overflow-hidden bg-gradient-to-br ${theme.gradient} font-sans text-slate-800">
        <div class="absolute top-[-5%] left-[-5%] w-[350px] h-[350px] ${theme.orbColor1} rounded-full mix-blend-multiply filter blur-[80px] opacity-60 animate-blob"></div>
        <div class="absolute bottom-[-5%] right-[-5%] w-[350px] h-[350px] ${theme.orbColor2} rounded-full mix-blend-multiply filter blur-[80px] opacity-60 animate-blob animation-delay-2000"></div>
        <div class="${theme.innerCard} w-full h-full min-h-[740px] flex flex-col relative z-10 overflow-hidden">
            ${innerHtml}
        </div>
    </div>`;
}

/** Cover Card — dispatches to layout-specific renderer */
function renderCoverCard(card, contentCards, theme, footer) {
    const layout = (card.layout || 'top-bottom').toLowerCase();
    switch (layout) {
        case 'center':
            return renderCoverCenter(card, theme, footer);
        case 'big-number':
            return renderCoverBigNumber(card, theme, footer);
        case 'top-bottom':
        default:
            return renderCoverTopBottom(card, contentCards, theme, footer);
    }
}

/** Cover — Top-Bottom Layout (default, with preview list) */
function renderCoverTopBottom(card, contentCards, theme, footer) {
    const pointsHtml = contentCards.slice(0, 3).map((c, i) => `
        <div class="flex items-start space-x-4">
            <div class="w-12 h-12 rounded-2xl ${theme.indexBg} flex items-center justify-center ${theme.indexText} font-bold text-xl flex-shrink-0">${String(i + 1).padStart(2, '0')}</div>
            <div>
                <h3 class="font-bold text-gray-800 text-lg">${c.cardTitle || ''}</h3>
                <p class="text-gray-400 text-sm mt-1">${getFirstBlockContent(c) || ''}</p>
            </div>
        </div>`).join('');

    const inner = `
        <div class="p-10 flex-1 flex flex-col justify-between relative z-20">
            <div>
                <span class="inline-block px-3 py-1 rounded-full ${theme.coverTagBg} ${theme.coverTagText} text-xs font-bold tracking-wider uppercase mb-6 backdrop-blur-sm">
                    ${card.categoryTag || card.tag || 'Topic'}
                </span>
                <h1 class="font-sans text-5xl font-bold text-slate-900 leading-[1.1] mb-4">
                    ${card.mainTitle || ''}<br/>
                    <span class="${theme.highlightText}">${card.subTitle || ''}</span>
                </h1>
            </div>
            <div class="space-y-6 mt-10">
                ${pointsHtml}
            </div>
            <div class="mt-auto pt-10 flex justify-between items-end border-t border-gray-100">
                <span class="text-[10px] font-bold tracking-widest uppercase opacity-40">${footer}</span>
                <span class="text-[10px] font-sans italic opacity-40">Nano Series</span>
            </div>
        </div>`;
    return renderRootContainer(inner, theme);
}

/** Cover — Center Focus Layout (big centered title, lots of whitespace) */
function renderCoverCenter(card, theme, footer) {
    const inner = `
        <div class="p-12 flex flex-col h-full min-h-[740px] justify-center text-center relative z-20">
            <span class="inline-block px-3 py-1 rounded-full ${theme.coverTagBg} ${theme.coverTagText} text-xs font-bold tracking-wider uppercase mb-10 mx-auto backdrop-blur-sm">
                ${card.categoryTag || card.tag || 'Topic'}
            </span>
            <h1 class="font-sans text-6xl font-bold text-slate-900 leading-[1.05] mb-8 px-4">
                ${card.mainTitle || ''}
            </h1>
            <div class="w-16 h-1 ${theme.checkFill} mx-auto rounded-full mb-8 opacity-60"></div>
            <p class="text-slate-400 text-base font-light tracking-widest uppercase px-12">
                ${card.subTitle || ''}
            </p>
            <div class="mt-auto pt-10 flex justify-between items-end opacity-40">
                <span class="text-[10px] font-bold tracking-widest uppercase">${footer}</span>
                <span class="text-[10px] font-sans italic">Nano Series</span>
            </div>
        </div>`;
    return renderRootContainer(inner, theme);
}

/** Cover — Big Number Layout (huge number as visual anchor) */
function renderCoverBigNumber(card, theme, footer) {
    const bigNumber = card.bigNumber || card.mainTitle || '';
    const title = card.bigNumber ? (card.mainTitle || '') : (card.subTitle || '');
    const subtitle = card.bigNumber ? (card.subTitle || '') : '';
    const inner = `
        <div class="p-10 flex flex-col h-full min-h-[740px] justify-center relative z-20">
            <span class="inline-block px-3 py-1 rounded-full ${theme.coverTagBg} ${theme.coverTagText} text-xs font-bold tracking-wider uppercase mb-8 backdrop-blur-sm w-fit">
                ${card.categoryTag || card.tag || 'Topic'}
            </span>
            <div class="relative mb-6">
                <div class="absolute -top-4 -left-2 text-[160px] font-bold ${theme.highlightText} opacity-[0.07] font-sans leading-none select-none pointer-events-none">${bigNumber}</div>
                <div class="text-8xl font-bold ${theme.highlightText} font-sans leading-none relative">${bigNumber}</div>
            </div>
            <div class="w-12 h-1 ${theme.checkFill} rounded-full mb-5"></div>
            <h1 class="font-sans text-2xl font-bold text-slate-900 leading-tight mb-3">
                ${title}
            </h1>
            <p class="text-slate-400 text-sm font-light tracking-wide">
                ${subtitle}
            </p>
            <div class="mt-auto pt-10 flex justify-between items-end opacity-40">
                <span class="text-[10px] font-bold tracking-widest uppercase">${footer}</span>
                <span class="text-[10px] font-sans italic">Nano Series</span>
            </div>
        </div>`;
    return renderRootContainer(inner, theme);
}

/** Content Card Header */
function renderHeader(card, theme) {
    return `
    <div class="p-8 pb-4 flex justify-between items-start">
        <div>
            <span class="${theme.topicText} font-bold text-xs tracking-[0.2em] uppercase mb-2 block">POINT ${String(card.index).padStart(2, '0')}</span>
            <h2 class="font-sans text-3xl font-bold text-slate-900 leading-tight">${card.cardTitle || ''}</h2>
        </div>
        <div class="w-12 h-12 ${theme.indexBg} rounded-full flex items-center justify-center ${theme.indexText} font-bold font-sans text-xl border ${theme.indexBorder}">
            ${card.index}
        </div>
    </div>`;
}

/** Concept Pill — for 观点块 (pain + solution) */
function renderConceptPill(block, theme) {
    const pain = block.pain || block.content || '';
    const solution = block.solution || '';
    return `
    <div class="px-8 mb-6">
        <div class="${theme.conceptBg} rounded-2xl p-5 border ${theme.conceptBorder}">
            <div class="flex gap-3 mb-2 items-start">
                <span class="flex-shrink-0 px-2 py-0.5 rounded ${theme.painBadgeBg} ${theme.painBadgeText} text-[10px] font-bold uppercase tracking-wide mt-0.5">Pain</span>
                <p class="text-sm text-slate-600 leading-relaxed">${pain}</p>
            </div>
            <div class="flex gap-3 items-start">
                <span class="flex-shrink-0 px-2 py-0.5 rounded ${theme.solBadgeBg} ${theme.solBadgeText} text-[10px] font-bold uppercase tracking-wide mt-0.5">Fix</span>
                <p class="text-sm text-slate-800 font-medium leading-relaxed">${solution}</p>
            </div>
        </div>
    </div>`;
}

/** Code Window — for 代码块 */
function renderCodeWindow(block, _theme) {
    const code = escapeHtml(block.content || '');
    return `
    <div class="px-8 mt-auto mb-8">
        <div class="bg-slate-900 rounded-2xl p-5 shadow-2xl relative overflow-hidden">
            <div class="flex gap-1.5 mb-4 opacity-50">
                <div class="w-2.5 h-2.5 rounded-full bg-red-500"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-yellow-500"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-green-500"></div>
            </div>
            <code class="block font-mono text-xs text-blue-200 leading-relaxed whitespace-pre-wrap font-light">${code}</code>
        </div>
    </div>`;
}

/** Checklist — for 清单块 */
function renderChecklist(block, theme) {
    const items = block.items || block.content?.split('\n').filter(Boolean) || [];
    const itemsHtml = items.map((item, i) => {
        const checked = i < Math.ceil(items.length / 2);
        return `
        <div class="flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-100 shadow-sm ${checked ? '' : 'opacity-60'}">
            <div class="w-5 h-5 rounded-full border-2 ${checked ? theme.checkBorder : 'border-slate-300'} flex items-center justify-center">
                ${checked ? `<div class="w-2.5 h-2.5 rounded-full ${theme.checkFill}"></div>` : ''}
            </div>
            <span class="text-sm ${checked ? 'text-slate-700 font-medium' : 'text-slate-500'}">${typeof item === 'string' ? item : item.text || ''}</span>
        </div>`;
    }).join('');
    return `<div class="px-8 space-y-3 mb-8">${itemsHtml}</div>`;
}

/** Glass Note — for 金句块 */
function renderGlassNote(block, theme) {
    return `
    <div class="mx-8 p-6 rounded-2xl ${theme.glassNoteBg} border ${theme.glassNoteBorder} text-center relative">
        <span class="absolute -top-3 left-1/2 -translate-x-1/2 bg-white px-2 py-0.5 text-[10px] font-bold ${theme.glassNoteLabel} tracking-widest uppercase shadow-sm rounded-full border border-slate-50">Note</span>
        <p class="${theme.glassNoteText} text-sm italic font-medium leading-relaxed">"${block.content || ''}"</p>
    </div>`;
}

/** Text Block — for 解释块 */
function renderTextBlock(block, _theme) {
    return `
    <div class="px-8 mb-6">
        <p class="text-sm text-slate-600 leading-relaxed">${(block.content || '').replace(/\n/g, '<br>')}</p>
    </div>`;
}

/** Stat Card — for 数据块 (1~3 number items side by side) */
function renderStatCard(block, theme) {
    const items = block.items || [{ number: block.content || '0', label: '' }];
    const itemsHtml = items.slice(0, 3).map(item => `
        <div class="flex-1 ${theme.conceptBg} rounded-2xl p-5 border ${theme.conceptBorder} text-center">
            <div class="text-4xl font-bold ${theme.indexText} font-sans leading-none mb-2">${item.number || ''}</div>
            <div class="text-xs text-slate-500 font-medium tracking-wide uppercase">${item.label || ''}</div>
        </div>`).join('');
    return `
    <div class="px-8 mb-6">
        <div class="flex gap-4">${itemsHtml}</div>
    </div>`;
}

/** VS Card — for 对比块 (before/after comparison) */
function renderVSCard(block, theme) {
    const before = block.before || '';
    const after = block.after || '';
    return `
    <div class="px-8 mb-6">
        <div class="grid grid-cols-2 gap-3">
            <div class="bg-red-50/50 rounded-2xl p-4 border border-red-100">
                <div class="flex items-center gap-2 mb-3">
                    <span class="w-6 h-6 rounded-full ${theme.painBadgeBg} flex items-center justify-center ${theme.painBadgeText} text-xs font-bold">\u2715</span>
                    <span class="text-xs font-bold ${theme.painBadgeText} uppercase tracking-wide">Before</span>
                </div>
                <p class="text-sm text-slate-600 leading-relaxed">${before}</p>
            </div>
            <div class="bg-emerald-50/50 rounded-2xl p-4 border border-emerald-100">
                <div class="flex items-center gap-2 mb-3">
                    <span class="w-6 h-6 rounded-full ${theme.solBadgeBg} flex items-center justify-center ${theme.solBadgeText} text-xs font-bold">\u2713</span>
                    <span class="text-xs font-bold ${theme.solBadgeText} uppercase tracking-wide">After</span>
                </div>
                <p class="text-sm text-slate-800 font-medium leading-relaxed">${after}</p>
            </div>
        </div>
    </div>`;
}

/** Step Flow — for 步骤块 (ordered vertical steps with connector) */
function renderStepFlow(block, theme) {
    const items = block.items || block.content?.split('\n').filter(Boolean) || [];
    const stepsHtml = items.map((item, i) => {
        const isLast = i === items.length - 1;
        const text = typeof item === 'string' ? item : item.text || '';
        return `
        <div class="flex gap-4 items-start">
            <div class="flex flex-col items-center">
                <div class="w-8 h-8 rounded-full ${theme.checkFill} flex items-center justify-center text-white text-xs font-bold flex-shrink-0">${i + 1}</div>
                ${isLast ? '' : `<div class="w-0.5 h-8 ${theme.conceptBg}"></div>`}
            </div>
            <div class="pt-1 ${isLast ? '' : 'pb-4'}">
                <p class="text-sm text-slate-700 font-medium leading-relaxed">${text}</p>
            </div>
        </div>`;
    }).join('');
    return `
    <div class="px-8 mb-6">
        <div class="space-y-0">${stepsHtml}</div>
    </div>`;
}

/** Highlight Box — for 高亮块 (key takeaway with accent left border) */
function renderHighlightBox(block, theme) {
    return `
    <div class="px-8 mb-6">
        <div class="${theme.conceptBg} rounded-2xl p-5 border-l-4 ${theme.checkBorder}">
            <p class="text-sm text-slate-800 font-medium leading-relaxed">${(block.content || '').replace(/\n/g, '<br>')}</p>
        </div>
    </div>`;
}

/** Image Block — for 图片块 (screenshot / image embed) */
function renderImageBlock(block, theme) {
    const src = block.src || '';
    const caption = block.caption || '';
    const isPlaceholder = block.placeholder || !src;

    if (isPlaceholder) {
        const desc = block.description || caption || '截图位置';
        return `
        <div class="px-8 mb-6">
            <div class="rounded-2xl overflow-hidden border-2 border-dashed ${theme.conceptBorder} ${theme.conceptBg} flex items-center justify-center" style="min-height: 200px;">
                <div class="text-center p-6">
                    <div class="text-3xl mb-3 opacity-30">\u{1F4F7}</div>
                    <p class="text-sm ${theme.topicText} font-medium">${desc}</p>
                </div>
            </div>
        </div>`;
    }

    const captionHtml = caption
        ? `<p class="text-xs text-slate-400 text-center mt-3 font-medium tracking-wide">${caption}</p>`
        : '';
    return `
    <div class="px-8 mb-6">
        <div class="rounded-2xl overflow-hidden border ${theme.conceptBorder} shadow-sm">
            <img src="${src}" alt="${caption}" class="w-full h-auto object-cover" style="max-height: 400px;" />
        </div>
        ${captionHtml}
    </div>`;
}

/** Footer */
function renderFooter(footer) {
    return `
    <div class="mt-auto p-8 pt-0 flex justify-between items-center opacity-40">
        <span class="text-[10px] font-bold tracking-widest uppercase">${footer}</span>
        <span class="text-[10px] font-sans italic">Nano Series</span>
    </div>`;
}

// ============================================================
// 4. Content Card Assembly
// ============================================================
function renderContentCard(card, theme, footer) {
    const blocks = card.blocks || [];
    let blocksHtml = '';

    for (const block of blocks) {
        switch (block.type) {
            case '观点块':
                blocksHtml += renderConceptPill(block, theme);
                break;
            case '代码块':
                blocksHtml += renderCodeWindow(block, theme);
                break;
            case '清单块':
                blocksHtml += renderChecklist(block, theme);
                break;
            case '金句块':
                blocksHtml += renderGlassNote(block, theme);
                break;
            case '解释块':
                blocksHtml += renderTextBlock(block, theme);
                break;
            case '数据块':
                blocksHtml += renderStatCard(block, theme);
                break;
            case '对比块':
                blocksHtml += renderVSCard(block, theme);
                break;
            case '步骤块':
                blocksHtml += renderStepFlow(block, theme);
                break;
            case '高亮块':
                blocksHtml += renderHighlightBox(block, theme);
                break;
            case '图片块':
                blocksHtml += renderImageBlock(block, theme);
                break;
            default:
                blocksHtml += renderTextBlock(block, theme);
        }
    }

    const inner = `
        ${renderHeader(card, theme)}
        <div class="flex-1 flex flex-col justify-center py-4">
            ${blocksHtml}
        </div>
        ${renderFooter(footer)}`;
    return renderRootContainer(inner, theme);
}

// ============================================================
// 5. Helpers
// ============================================================
function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function getFirstBlockContent(card) {
    const block = (card.blocks || []).find(b => b.type === '观点块' || b.type === '解释块');
    if (!block) return '';
    return block.pain || block.content || '';
}

function sanitizeFilename(str) {
    return str
        .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]/gu, '')
        .replace(/[\\/:*?"<>|]/g, '')
        .replace(/\s+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '')
        .substring(0, 50);
}

/** Normalize data from various input formats */
function normalizeData(data) {
    const normalized = JSON.parse(JSON.stringify(data));

    if (!normalized.analysis) {
        normalized.analysis = { coreValue: '', emotionalHook: '' };
    }
    if (!normalized.xiaohongshuPost) {
        normalized.xiaohongshuPost = {
            title: normalized.topic || 'Untitled',
            tags: ['#分享'],
        };
    }
    if (!normalized.theme) {
        normalized.theme = { style: 'tech' };
    }

    if (normalized.cards) {
        normalized.cards = normalized.cards
            .map((card, index) => {
                const c = { ...card };
                if (card.type === 'cover') c.type = '封面卡';
                else if (card.type === 'content' || card.type === 'pain_point' || card.type === 'core_feature' || card.type === 'action' || card.type === 'scenarios') c.type = '内容卡';
                else if (c.type !== '封面卡' && c.type !== '内容卡') c.type = '内容卡';

                if (card.title && !c.mainTitle) c.mainTitle = card.title;
                if (card.title && !c.cardTitle) c.cardTitle = card.title;
                if (card.subtitle && !c.subTitle) c.subTitle = card.subtitle;
                if (!c.blocks) {
                    c.blocks = [];
                    if (card.content) c.blocks.push({ type: '解释块', content: card.content });
                }
                if (!c.index && c.type === '内容卡') c.index = String(index).padStart(2, '0');
                return c;
            })
            .filter(c => c.type === '封面卡' || c.type === '内容卡');
    }
    return normalized;
}

// ============================================================
// 6. Main Generator
// ============================================================
async function generateNano(jsonPath, outputDir) {
    try {
        const rawData = await fs.readFile(jsonPath, 'utf8');
        let data = JSON.parse(rawData);
        data = normalizeData(data);

        const themeKey = getTheme(data);
        const theme = THEMES[themeKey];
        const footer = process.env.CARD_FOOTER || '@你的昵称';

        // Resolve image paths in 图片块 to absolute file:// URLs
        const jsonDir = path.dirname(path.resolve(jsonPath));
        for (const card of data.cards || []) {
            for (const block of card.blocks || []) {
                if (block.type === '图片块' && block.src && !block.placeholder) {
                    if (!block.src.startsWith('http') && !block.src.startsWith('file:')) {
                        const absPath = path.resolve(jsonDir, block.src);
                        block.src = 'file:///' + absPath.replace(/\\/g, '/');
                    }
                }
            }
        }

        console.log(`🎨 Theme: ${themeKey}`);

        const coverCard = data.cards.find(c => c.type === '封面卡') || data.cards[0];
        const contentCards = data.cards.filter(c => c.type === '内容卡');

        // Read template
        const templatePath = path.join(__dirname, '../模板/nano-template.html');
        let html = await fs.readFile(templatePath, 'utf8');

        // Build all cards HTML
        const allCardsHtml = [
            renderCoverCard(coverCard, contentCards, theme, footer),
            ...contentCards.map(c => renderContentCard(c, theme, footer)),
        ].join('\n');

        html = html.replace('{{ALL_CARDS_HTML}}', allCardsHtml);

        // Output directory — default to same dir as input JSON
        const resolvedJsonPath = path.resolve(jsonPath);
        const finalOutputDir = outputDir
            ? path.resolve(outputDir)
            : path.dirname(resolvedJsonPath);

        const title = sanitizeFilename(data.xiaohongshuPost?.title || 'Untitled');

        console.log(`📂 Output: ${finalOutputDir}`);
        await fs.mkdir(finalOutputDir, { recursive: true });

        const htmlPath = path.join(finalOutputDir, `${title}_nano.html`);
        await fs.writeFile(htmlPath, html, 'utf8');
        console.log(`✅ HTML: ${htmlPath}`);

        // Screenshot with Puppeteer
        console.log('📸 Generating screenshots...');
        const browser = await puppeteer.launch({
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
        });

        let cardCount = 0;
        try {
            const page = await browser.newPage();
            await page.setViewport({ width: 1080, height: 2000, deviceScaleFactor: 2 });
            await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
            await new Promise(r => setTimeout(r, 1500));

            const cards = await page.$$('.card-container');
            cardCount = cards.length;
            console.log(`🔍 Found ${cardCount} cards`);

            for (let i = 0; i < cards.length; i++) {
                const cardType = i === 0 ? 'cover' : `content_${i}`;
                const filename = `card_${String(i + 1).padStart(2, '0')}_${cardType}.png`;
                const filepath = path.join(finalOutputDir, filename);
                await cards[i].screenshot({ path: filepath, type: 'png' });
                console.log(`✅ ${filename}`);
            }
        } finally {
            await browser.close();
        }

        // Save post text
        if (data.xiaohongshuPost) {
            const post = data.xiaohongshuPost;
            const txt = `【标题】\n${post.title}\n\n【正文】\n${post.body || ''}\n\n【标签】\n${(post.tags || []).join(' ')}\n`;
            await fs.writeFile(path.join(finalOutputDir, 'xiaohongshu-post.txt'), txt, 'utf8');
            console.log('📝 xiaohongshu-post.txt');
        }

        console.log(`\n🎉 Done! ${cardCount} cards generated at ${finalOutputDir}`);
        return htmlPath;
    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
}

// ============================================================
// 7. CLI
// ============================================================
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log('Usage: node generate-nano.js <data.json> [output-dir]');
        process.exit(0);
    }
    generateNano(args[0], args[1]);
}

module.exports = { generateNano };
