import {
  AbsoluteFill,
  Series,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { FC } from "react";
import { z } from "zod";
import { ArticleVideoProps } from "./utils/markdownParser";

export const articleVideoSchema = z.object({
  title: z.string(),
  coreInsight: z.string(),
  sections: z.array(
    z.object({
      title: z.string(),
      points: z.array(z.string()),
    }),
  ),
});

const TitleScene: FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{ justifyContent: "center", alignItems: "center", padding: 40 }}
    >
      <h1
        style={{
          fontSize: 80,
          fontWeight: "bold",
          textAlign: "center",
          transform: `scale(${spring({ frame, fps, config: { damping: 200 } })})`,
          opacity,
        }}
      >
        {title}
      </h1>
    </AbsoluteFill>
  );
};

const InsightScene: FC<{ coreInsight: string }> = ({ coreInsight }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
        backgroundColor: "#222",
      }}
    >
      <h2 style={{ fontSize: 40, color: "#aaa", marginBottom: 20, opacity }}>
        核心洞见
      </h2>
      <p
        style={{
          fontSize: 50,
          textAlign: "center",
          lineHeight: 1.4,
          opacity: interpolate(frame, [0, 20], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {coreInsight}
      </p>
    </AbsoluteFill>
  );
};

const SectionScene: FC<{ section: ArticleVideoProps["sections"][0] }> = ({
  section,
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ padding: 60, justifyContent: "center" }}>
      <h2
        style={{
          fontSize: 60,
          marginBottom: 40,
          color: "#64ffda",
          opacity: interpolate(frame, [0, 15], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {section.title}
      </h2>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {section.points.map((point, i) => (
          <li
            key={i}
            style={{
              fontSize: 40,
              lineHeight: 1.6,
              marginBottom: 20,
              opacity: interpolate(
                frame,
                [10 + i * 10, 20 + i * 10],
                [0, 1],
                { extrapolateRight: "clamp" },
              ),
              transform: `translateX(${interpolate(
                frame,
                [10 + i * 10, 30 + i * 10],
                [50, 0],
                { extrapolateRight: "clamp" },
              )}px)`,
            }}
          >
            • {point}
          </li>
        ))}
      </ul>
    </AbsoluteFill>
  );
};

export const ArticleVideo: FC<ArticleVideoProps> = ({
  title,
  coreInsight,
  sections,
}) => {
  const { fps } = useVideoConfig();

  // Define durations in seconds for easier tuning
  const titleDurationInSeconds = 3;
  const insightDurationInSeconds = 5;
  const sectionDurationInSeconds = 6.6; // approx 200 frames at 30fps

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#111",
        color: "white",
        fontFamily: "sans-serif",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Series>
        <Series.Sequence
          durationInFrames={Math.floor(titleDurationInSeconds * fps)}
        >
          <TitleScene title={title} />
        </Series.Sequence>

        <Series.Sequence
          durationInFrames={Math.floor(insightDurationInSeconds * fps)}
        >
          <InsightScene coreInsight={coreInsight} />
        </Series.Sequence>

        {sections.map((section, index) => (
          <Series.Sequence
            key={index}
            durationInFrames={Math.floor(sectionDurationInSeconds * fps)}
          >
            <SectionScene section={section} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
