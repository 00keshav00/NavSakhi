"use client";

import React, { useMemo } from "react";

interface MarkdownMessageProps {
  content: string;
  className?: string;
  isUser?: boolean;
}

/**
 * Lightweight, accessible, zero-dependency Markdown renderer for NavSakhi assistant messages.
 * Formats:
 * - Headings (###, ##, #)
 * - Numbered steps (1., 2., etc.)
 * - Bullet lists (-, *, •)
 * - Bold emphasis (**text**)
 * - Inline code (`text`)
 * - Blockquotes (> quote)
 * - Paragraphs with clear spacing
 * - Phone links for emergency numbers (112, 1091, 100, 108)
 */
export function MarkdownMessage({ content, className = "", isUser = false }: MarkdownMessageProps) {
  const elements = useMemo(() => {
    if (!content) return null;
    if (isUser) {
      return <p className="whitespace-pre-wrap">{content}</p>;
    }

    const lines = content.split("\n");
    const blocks: React.ReactNode[] = [];
    let currentList: { type: "ol" | "ul"; items: string[] } | null = null;
    let blockIndex = 0;

    const flushList = () => {
      if (currentList) {
        const ListTag = currentList.type;
        const listItems = currentList.items.map((item, idx) => (
          <li key={idx} className="leading-relaxed">
            {formatInlineText(item)}
          </li>
        ));
        blocks.push(
          <ListTag
            key={`list-${blockIndex++}`}
            className={`my-2 space-y-1 pl-5 ${
              currentList.type === "ol" ? "list-decimal" : "list-disc"
            }`}
          >
            {listItems}
          </ListTag>
        );
        currentList = null;
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      if (!line) {
        flushList();
        continue;
      }

      // Headings
      if (line.startsWith("### ")) {
        flushList();
        blocks.push(
          <h4 key={`h3-${blockIndex++}`} className="font-bold text-sm text-foreground mt-3 mb-1">
            {formatInlineText(line.slice(4))}
          </h4>
        );
        continue;
      }
      if (line.startsWith("## ")) {
        flushList();
        blocks.push(
          <h3 key={`h2-${blockIndex++}`} className="font-extrabold text-base text-foreground mt-3 mb-1">
            {formatInlineText(line.slice(3))}
          </h3>
        );
        continue;
      }
      if (line.startsWith("# ")) {
        flushList();
        blocks.push(
          <h2 key={`h1-${blockIndex++}`} className="font-extrabold text-lg text-foreground mt-3.5 mb-1.5">
            {formatInlineText(line.slice(2))}
          </h2>
        );
        continue;
      }

      // Blockquotes
      if (line.startsWith("> ")) {
        flushList();
        blocks.push(
          <blockquote
            key={`quote-${blockIndex++}`}
            className="border-l-2 border-primary/60 pl-3 my-2 text-xs italic text-muted-foreground bg-primary/5 py-1 rounded-r-md"
          >
            {formatInlineText(line.slice(2))}
          </blockquote>
        );
        continue;
      }

      // Numbered list item: "1. ", "2. ", etc.
      const olMatch = line.match(/^(\d+)\.\s+(.*)$/);
      if (olMatch) {
        if (!currentList || currentList.type !== "ol") {
          flushList();
          currentList = { type: "ol", items: [] };
        }
        currentList.items.push(olMatch[2]);
        continue;
      }

      // Bullet list item: "- ", "* ", "• "
      const ulMatch = line.match(/^[-*•]\s+(.*)$/);
      if (ulMatch) {
        if (!currentList || currentList.type !== "ul") {
          flushList();
          currentList = { type: "ul", items: [] };
        }
        currentList.items.push(ulMatch[1]);
        continue;
      }

      // Regular paragraph line
      flushList();
      blocks.push(
        <p key={`p-${blockIndex++}`} className="my-1.5 leading-relaxed">
          {formatInlineText(line)}
        </p>
      );
    }

    flushList();
    return blocks;
  }, [content, isUser]);

  return <div className={`text-sm leading-relaxed space-y-1 ${className}`}>{elements}</div>;
}

/**
 * Formats inline elements: **bold**, `code`, and emergency telephone numbers.
 */
function formatInlineText(text: string): React.ReactNode {
  // Split on bold markdown **...** and inline code `...`
  const tokens = text.split(/(\*\*.*?\*\*|`.*?`)/g);

  return tokens.map((token, idx) => {
    if (token.startsWith("**") && token.endsWith("**") && token.length >= 4) {
      const inner = token.slice(2, -2);
      return (
        <strong key={idx} className="font-semibold text-foreground">
          {linkEmergencyNumbers(inner)}
        </strong>
      );
    }
    if (token.startsWith("`") && token.endsWith("`") && token.length >= 2) {
      const inner = token.slice(1, -1);
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-muted/80 font-mono text-xs text-primary"
        >
          {inner}
        </code>
      );
    }
    return linkEmergencyNumbers(token, idx);
  });
}

/**
 * Replaces emergency phone numbers (112, 1091, 100, 108) with clickable tel: anchors.
 */
function linkEmergencyNumbers(text: string, keyPrefix: number = 0): React.ReactNode {
  const parts = text.split(/\b(112|1091|100|108)\b/g);
  if (parts.length === 1) {
    return text;
  }

  return parts.map((part, pIdx) => {
    if (["112", "1091", "100", "108"].includes(part)) {
      return (
        <a
          key={`tel-${keyPrefix}-${pIdx}`}
          href={`tel:${part}`}
          className="font-bold underline text-rose-500 hover:text-rose-400 mx-0.5"
          title={`Call ${part} immediately`}
        >
          {part}
        </a>
      );
    }
    return part;
  });
}
