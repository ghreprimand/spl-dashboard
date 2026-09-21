export interface Layout {
  width: number;
  height: number;
  fontSize: number;
  x: number;
  y: number;
  gap: number;
  spectrum: boolean;
  details: boolean;
}
export const defaultLayout: Layout = {
  width: 1280,
  height: 100,
  fontSize: 40,
  x: 50,
  y: 0,
  gap: 10,
  spectrum: true,
  details: true,
};
export function normalizeLayout(value: unknown): Layout {
  const v = (
    value && typeof value === "object" ? value : {}
  ) as Partial<Layout>;
  const number = (key: keyof Layout, min: number, max: number): number => {
    const n = v[key];
    return typeof n === "number" && Number.isFinite(n)
      ? Math.max(min, Math.min(max, n))
      : (defaultLayout[key] as number);
  };
  return {
    width: number("width", 320, 2000),
    height: number("height", 64, 200),
    fontSize: number("fontSize", 20, 64),
    x: number("x", 0, 100),
    y: number("y", 0, 100),
    gap: number("gap", 2, 24),
    spectrum: typeof v.spectrum === "boolean" ? v.spectrum : true,
    details: typeof v.details === "boolean" ? v.details : true,
  };
}
export function loadLayout(): Layout {
  try {
    return normalizeLayout(
      JSON.parse(localStorage.getItem("spl-layout-v1") ?? "{}"),
    );
  } catch {
    return defaultLayout;
  }
}
