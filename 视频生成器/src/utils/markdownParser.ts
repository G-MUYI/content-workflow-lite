
export interface ArticleVideoProps {
	[key: string]: unknown;
	title: string;
	coreInsight: string;
	sections: {
		title: string;
		points: string[];
	}[];
}

export const parseArticleMarkdown = (markdown: string): ArticleVideoProps => {
	const lines = markdown.split('\n');
	let title = '';
	let coreInsight = '';
	const sections: { title: string; points: string[] }[] = [];

	let currentSection: { title: string; points: string[] } | null = null;
	let inContentStructure = false;
	let inCoreInsight = false;

	// Extract title from YAML frontmatter
	if (lines[0]?.trim() === '---') {
		for (let i = 1; i < lines.length; i++) {
			const line = lines[i].trim();
			if (line === '---') break;
			const titleMatch = line.match(/^title:\s*"?(.+?)"?\s*$/);
			if (titleMatch) {
				title = titleMatch[1];
			}
		}
	}

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i].trim();

		// Fallback: extract title from H1 if not found in frontmatter
		if (line.startsWith('# ') && !title) {
			title = line.substring(2).trim();
		}

		// Extract Core Insight — support both formats:
		// 1. `## 核心洞见` (standalone)
		// 2. `### 核心洞见` (under ## 选题评估)
		if (line === '## 核心洞见' || line === '### 核心洞见') {
			inCoreInsight = true;
			continue;
		}
		if (inCoreInsight) {
			if (line.startsWith('>')) {
				coreInsight = line.replace(/^>\s*/, '').trim();
				inCoreInsight = false;
			} else if (line.startsWith('##')) {
				inCoreInsight = false;
			}
		}

		// Extract Content Structure — support both formats:
		// 1. `## 内容结构` (standalone)
		// 2. `### 内容结构` (under ## 内容策划)
		if (line === '## 内容结构' || line === '### 内容结构') {
			inContentStructure = true;
			continue;
		}

		if (inContentStructure) {
			// End when hitting a same-level or higher heading
			if ((line.startsWith('## ') && !line.startsWith('### ')) ||
				(line.startsWith('### ') && !line.startsWith('#### '))) {
				// Check if this is a new section within 内容结构 (####) or end of it
				if (line.startsWith('### ') && inContentStructure) {
					// Could be a sibling ### under ## 内容策划 — end content structure
					inContentStructure = false;
					if (currentSection) {
						sections.push(currentSection);
						currentSection = null;
					}
				}
				if (line.startsWith('## ')) {
					inContentStructure = false;
					if (currentSection) {
						sections.push(currentSection);
						currentSection = null;
					}
				}
			} else if (line.startsWith('#### ') || line.startsWith('### ')) {
				// New section within content structure
				if (currentSection) {
					sections.push(currentSection);
				}
				const prefix = line.startsWith('#### ') ? 5 : 4;
				currentSection = {
					title: line.substring(prefix).trim(),
					points: []
				};
			} else if (currentSection) {
				if (line.match(/^\d+\./) || line.startsWith('- ')) {
					currentSection.points.push(line.replace(/^(\d+\.|-)\s*/, '').trim());
				} else if (line.length > 0 && !line.startsWith('!') && !line.startsWith('<')) {
					currentSection.points.push(line);
				}
			}
		}
	}
	if (currentSection) {
		sections.push(currentSection);
	}

	return {
		title,
		coreInsight,
		sections
	};
};
