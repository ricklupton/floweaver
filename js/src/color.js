/**
 * Color handling: categorical lookups and quantitative interpolation.
 */

/**
 * Parse a hex color string to [r, g, b].
 * @param {string} hex - e.g. "#ff00aa"
 * @returns {number[]}
 */
function hexToRgb(hex) {
  hex = hex.replace(/^#/, "");
  return [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ];
}

/**
 * Interpolate within a palette at position t ∈ [0, 1].
 * @param {string[]} palette - Array of hex color strings
 * @param {number} t
 * @returns {string} Hex color
 */
export function interpolateColor(palette, t) {
  if (!palette || palette.length === 0) return "#cccccc";

  const idx = t * (palette.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, palette.length - 1);

  if (lo === hi) return palette[lo];

  const frac = idx - lo;
  const cLo = hexToRgb(palette[lo]);
  const cHi = hexToRgb(palette[hi]);

  const r = Math.floor(cLo[0] + frac * (cHi[0] - cLo[0]));
  const g = Math.floor(cLo[1] + frac * (cHi[1] - cLo[1]));
  const b = Math.floor(cLo[2] + frac * (cHi[2] - cLo[2]));

  return (
    "#" +
    r.toString(16).padStart(2, "0") +
    g.toString(16).padStart(2, "0") +
    b.toString(16).padStart(2, "0")
  );
}

/**
 * Compute the color for a link given an edge, aggregated data, and display spec.
 *
 * @param {object} edge       - EdgeSpec from the WeaverSpec
 * @param {object} data       - Aggregated measure values {column: number}
 * @param {object} displaySpec - {link_width, link_color}
 * @returns {string} Hex color string
 */
export function applyColor(edge, data, displaySpec) {
  const colorSpec = displaySpec.link_color;

  if (colorSpec.type === "categorical") {
    const attr = colorSpec.attr;
    let value;
    if (attr === "type") value = edge.type;
    else if (attr === "source") value = edge.source;
    else if (attr === "target") value = edge.target;
    else if (attr === "time") value = edge.time;
    else value = data[attr];

    return colorSpec.lookup[String(value)] ?? colorSpec.default;
  }

  if (colorSpec.type === "quantitative") {
    let value = data[colorSpec.attr] ?? 0.0;

    if (colorSpec.intensity != null) {
      const intensityValue = data[colorSpec.intensity] ?? 1.0;
      if (intensityValue !== 0) {
        value = value / intensityValue;
      }
    }

    const [dMin, dMax] = colorSpec.domain;
    let normed;
    if (dMax !== dMin) {
      normed = (value - dMin) / (dMax - dMin);
    } else {
      normed = 0.5;
    }
    normed = Math.max(0.0, Math.min(1.0, normed));

    return interpolateColor(colorSpec.palette, normed);
  }

  return "#cccccc";
}
