export const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

export const compact = (n: number) => n.toLocaleString("en-IN");

export const pct = (fraction: number) => (fraction * 100).toFixed(1) + "%";

export const roasX = (n: number) => n.toFixed(1) + "×";
