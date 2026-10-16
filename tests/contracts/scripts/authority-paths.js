// SPDX-License-Identifier: Apache-2.0
// Mutable operator evidence must never be created in the reviewed source checkout.
const fs = require('fs');
const path = require('path');
const SOURCE_ROOT = fs.realpathSync(path.resolve(__dirname, '../../..'));
function inside(root, target) {
    const relative = path.relative(root, target);
    return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}
function assertOutsideCheckout(filename) {
    if (typeof filename !== 'string' || filename.length === 0) throw Error('Explicit operator path required');
    const target = path.resolve(filename), suffix = [];
    let ancestor = target;
    while (true) {
        try { fs.lstatSync(ancestor); break; }
        catch (error) { if (error.code !== 'ENOENT') throw error; suffix.unshift(path.basename(ancestor)); ancestor = path.dirname(ancestor); }
    }
    const resolved = path.resolve(fs.realpathSync(ancestor), ...suffix);
    if (inside(SOURCE_ROOT, target) || inside(SOURCE_ROOT, resolved)) {
        const error = Error('Mutable operator paths must remain outside the reviewed checkout, including ignored paths and symlink aliases');
        error.publicMessage = true; throw error;
    }
    return target;
}
module.exports = { SOURCE_ROOT, assertOutsideCheckout };
