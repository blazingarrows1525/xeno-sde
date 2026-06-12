import { Fragment, type ReactNode } from "react";

// Minimal, dependency-free markdown renderer for the agent's proposed plan
// (headings, bullets, bold, rules). Good enough for the model's markdown output.
function renderInline(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="font-semibold text-slate-100">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}

export function AgentPlanText({ text }: { text: string }) {
  return (
    <div className="space-y-0.5">
      {text.split("\n").map((raw, i) => {
        const line = raw.trimEnd();
        if (!line.trim()) return <div key={i} className="h-2" />;
        if (/^#{1,6}\s/.test(line)) {
          return (
            <div key={i} className="mb-1 mt-3 text-sm font-semibold text-indigo-200">
              {renderInline(line.replace(/^#{1,6}\s*/, ""))}
            </div>
          );
        }
        if (/^---+$/.test(line.trim())) {
          return <hr key={i} className="my-3 border-white/[0.07]" />;
        }
        if (/^\s*[-*]\s+/.test(line)) {
          return (
            <div key={i} className="flex gap-2 text-sm text-slate-300">
              <span className="text-indigo-400">•</span>
              <span>{renderInline(line.replace(/^\s*[-*]\s+/, ""))}</span>
            </div>
          );
        }
        return (
          <div key={i} className="text-sm leading-relaxed text-slate-300">
            {renderInline(line)}
          </div>
        );
      })}
    </div>
  );
}
