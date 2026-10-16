import { canonical, parseBounded } from './vendor/alpha/docs/assets/successor/engine.mjs';
export function adaptExecutionSpec(spec) {
  let compiledName = '';
  for (const scalar of spec.name.normalize('NFC')) {
    if (compiledName.length + scalar.length > 48) break;
    compiledName += scalar;
  }
  if (!compiledName.trim()) compiledName = 'SUCCESSOR Ω';
  const adapted = parseBounded(canonical(spec));
  adapted.name = compiledName;
  const compiledLicense = spec.rights.license.normalize('NFC');
  if (compiledLicense.length > 1000) throw Object.assign(Error('JOBS_PROJECT_LICENSE_NORMALIZATION_UNAVAILABLE'), { code: 'JOBS_PROJECT_LICENSE_NORMALIZATION_UNAVAILABLE' });
  adapted.rights.license = compiledLicense;
  return { spec: adapted, licenseMapping: { policy: 'unicode-nfc-within-native-limit/v1', originalLicense: spec.rights.license, compiledLicense, maximumUtf16Units: 1000 }, mapping: { policy: 'nfc-unicode-scalar-prefix-48-or-successor-label/v1', originalName: spec.name, compiledName, maximumUtf16Units: 48 } };
}
