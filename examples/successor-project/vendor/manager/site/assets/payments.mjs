const SCALE = 1_000_000n;
export function parseUSDC(value) {
  const text = String(value).trim();
  if (!/^\d{1,18}(?:\.\d{1,6})?$/.test(text)) throw new Error("amount");
  const [whole, fraction = ""] = text.split(".");
  const amount = BigInt(whole) * SCALE + BigInt(fraction.padEnd(6, "0"));
  if (amount <= 0n) throw new Error("amount");
  return amount;
}
export function splitPayment(value, rate = 8) {
  const cost = parseUSDC(value);
  if (!/^\d{1,2}$/.test(String(rate)) || Number(rate) < 1 || Number(rate) > 60)
    throw new Error("rate");
  const validators = (cost * BigInt(rate)) / 100n,
    wallet30 = (cost * 30n) / 100n,
    wallet10 = (cost * 10n) / 100n;
  return {
    cost,
    agent: cost - validators - wallet30 - wallet10,
    validators,
    wallet30,
    wallet10,
  };
}
export function formatUSDC(amount, lang = "en") {
  const whole = (amount / SCALE).toLocaleString(
    lang === "fr" ? "fr-CA" : "en-CA",
  );
  const fraction = (amount % SCALE)
    .toString()
    .padStart(6, "0")
    .replace(/0+$/, "");
  return (
    whole + (fraction ? (lang === "fr" ? "," : ".") + fraction : "") + " USDC"
  );
}
