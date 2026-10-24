/**
 * Money maths in the browser, exactly as the server does it (design D5; edge case #6).
 *
 * Amounts stay decimal strings, as the API sends them. JavaScript numbers are binary
 * floating point and can't hold every amount exactly, so the maths runs on scaled
 * integers (BigInt) and rounds half up, like Python's ROUND_HALF_UP.
 */

type Scaled = { units: bigint; scale: number };

const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;
const pow10 = (exponent: number) => 10n ** BigInt(exponent);

function parse(text: string): Scaled {
  const match = DECIMAL.exec(text.trim());
  if (!match) throw new Error(`Not a plain decimal number: ${text}`);
  const [, sign, whole, fraction = ""] = match;
  return { units: BigInt(whole + fraction) * (sign ? -1n : 1n), scale: fraction.length };
}

function format({ units, scale }: Scaled): string {
  const digits = (units < 0n ? -units : units).toString().padStart(scale + 1, "0");
  const text = scale ? `${digits.slice(0, -scale)}.${digits.slice(-scale)}` : digits;
  return units < 0n ? `-${text}` : text;
}

/** a ÷ b, rounded half away from zero. */
function divide(a: bigint, b: bigint): bigint {
  const [x, y] = [a < 0n ? -a : a, b < 0n ? -b : b];
  const quotient = (2n * x + y) / (2n * y);
  return a < 0n !== b < 0n ? -quotient : quotient;
}

function rescale(value: Scaled, scale: number): Scaled {
  if (scale >= value.scale) return { units: value.units * pow10(scale - value.scale), scale };
  return { units: divide(value.units, pow10(value.scale - scale)), scale };
}

/** Whether text is a plain number with at most `minorUnits` decimals. */
export function isAmount(text: string, minorUnits: number): boolean {
  const match = DECIMAL.exec(text.trim());
  return match !== null && !match[1] && (match[3] ?? "").length <= minorUnits;
}

/** Round half up to the currency's step: 2 decimals for INR, none for JPY, 3 for KWD. */
export function roundToMinorUnit(amount: string, minorUnits: number): string {
  return format(rescale(parse(amount), minorUnits));
}

/** The amount after a % change, as the preview shows it and the form sends it. */
export function applyRaise(amount: string, percent: string, minorUnits: number): string {
  const base = parse(amount);
  const change = parse(percent);
  // amount × (100 + percent) ÷ 100, kept exact until the final rounding.
  const factor = 100n * pow10(change.scale) + change.units;
  const exact = { units: base.units * factor, scale: base.scale + change.scale + 2 };
  return format(rescale(exact, minorUnits));
}

/** The % change from one amount to another, to one decimal: "7.0" for 1800000 → 1926000. */
export function raisePercent(previous: string, current: string): string {
  const scale = Math.max(parse(previous).scale, parse(current).scale);
  const before = rescale(parse(previous), scale).units;
  const after = rescale(parse(current), scale).units;
  return format({ units: divide((after - before) * 1000n, before), scale: 1 });
}

/** An amount in its currency, written the way the country writes it: en-IN gives ₹18,00,000.
 *  Whole amounts drop their zero decimals; others show the currency's own number of them. */
export function formatMoney(
  amount: string,
  currency: string,
  locale: string,
  minorUnits: number,
): string {
  const digits = /^-?\d+(\.0+)?$/.test(amount) ? 0 : minorUnits;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(amount as Intl.StringNumericLiteral);
}

/** A large amount in short form for headline numbers, such as $461M, or ₹658.5Cr in India.
 *  Display only: tables keep the exact amount. */
export function formatCompact(amount: string, currency: string, locale: string): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(amount as Intl.StringNumericLiteral);
}
