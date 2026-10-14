import { ArticleVideoProps } from "./utils/markdownParser";

// 示例数据：换成你自己的文章内容后再渲染
export const articleData: ArticleVideoProps = {
  title: "示例标题",
  coreInsight: "示例核心观点。换成你自己的内容。",
  sections: [
    {
      title: "开头：别急着学Skills",
      points: [
        "最近很多人问我怎么学skills，我的回答是——别学了。",
        "不是skills不好，是你可能搞错了重点。"
      ]
    },
    {
      title: "1. 90%的人搞错了重点",
      points: [
        "很多人以为skills是全新的技术",
        "实际上它本质就是提示词，换了种组织方式"
      ]
    },
    {
      title: "2. Skills vs 传统提示词",
      points: [
        "传统：散落各处、一次性、单点",
        "Skills：统一管理、可迭代、可串联",
        "关键词：工程化封装"
      ]
    },
    {
      title: "3. 什么时候需要升级？",
      points: [
        "判断标准：你有没有一个\"常用提示词\"？",
        "如果你连一个提示词都没用顺，别急着学skills",
        "先把一个提示词用好，再升级"
      ]
    },
    {
      title: "结尾：从写好提示词开始",
      points: [
        "Skills的价值不在于\"新\"，而在于\"组织\"。",
        "但如果你连要组织的东西都没有，学skills就是空中楼阁。",
        "所以别焦虑，先从写好一个提示词开始。"
      ]
    }
  ]
};
