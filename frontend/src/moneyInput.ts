export function parseMoney(value: string) {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) throw new Error('Use nonnegative USD amounts with at most two decimal places.');
  const [whole = '', fraction = ''] = value.split('.');
  const result = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(result) || result > 1_000_000_000_000) throw new Error('That USD amount exceeds the supported limit.');
  return result;
}
