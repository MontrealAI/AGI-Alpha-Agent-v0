// SPDX-License-Identifier: Apache-2.0
// Pure, deliberately restricted Git-config syntax audit. No Git or filesystem calls.
import assert from 'node:assert/strict';

const SECTIONS = new Set(['core', 'remote', 'branch', 'extensions', 'http', 'gc']);
const DENIED = new Set(['fsmonitor', 'worktree', 'hookspath', 'attributesfile', 'uploadpack',
    'receivepack', 'promisor', 'partialclone', 'alternaterefscommand', 'sshcommand', 'gitproxy',
    'vcs', 'include', 'includeif', 'protocol']);
const FALSE = new Set(['false', 'no', 'off', '0']);

function configRows(text, ignoredWorktree = false) {
    assert.ok(typeof text === 'string' && Buffer.byteLength(text) <= 128000
        && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text), 'Bounded Git configuration text required');
    let section = null, subsection = null;
    const rows = [];
    for (const raw of text.split(/\r?\n/)) {
        let quoted = false, line = '';
        for (const character of raw) {
            if (!quoted && (character === '#' || character === ';')) break;
            assert.notEqual(character, '\\', 'Continued or escaped Git configuration is refused');
            if (character === '"') quoted = !quoted;
            line += character;
        }
        assert.equal(quoted, false, 'Multiline Git configuration is refused');
        line = line.trim();
        if (!line) continue;
        if (line.startsWith('[')) {
            const match = /^\[([A-Za-z][A-Za-z0-9-]*)(?:\s+"([^"\\]*)")?\]$/.exec(line);
            assert.ok(match && (SECTIONS.has(match[1].toLowerCase())
                || (ignoredWorktree && match[1].toLowerCase() === 'index')), 'Unexpected local Git configuration section');
            section = match[1].toLowerCase(); subsection = match[2] ?? null;
            assert.ok(subsection === null || ['remote', 'branch', 'http'].includes(section),
                'Unexpected local Git configuration subsection');
            continue;
        }
        const match = /^([A-Za-z][A-Za-z0-9-]*)(?:\s*=\s*(.*))?$/.exec(line);
        assert.ok(section && match, 'Unrecognized local Git configuration syntax');
        const key = match[1].toLowerCase(), value = match[2]?.trim();
        assert.ok(!DENIED.has(key), 'Executable, lazy-fetch or redirected Git configuration is refused');
        rows.push({section, subsection, key, value});
    }
    return rows;
}

/** Git 2.55 reads config.worktree only with extensions.worktreeConfig enabled.
 * https://git-scm.com/docs/git-config/2.55.0#Documentation/git-config.txt-worktreeConfig
 * Every enabling, bare, continued or unknown value is refused, including duplicates.
 */
export function auditGitConfiguration(config, ignoredWorktree = null) {
    const rows = configRows(config);
    for (const row of rows) {
        if (row.section === 'gc') {
            assert.ok(row.subsection === null && row.key === 'auto' && row.value === '0',
                'Only disabled automatic Git garbage collection is admitted');
        }
        if (row.key === 'worktreeconfig') {
            assert.ok(row.section === 'extensions' && row.subsection === null
                && FALSE.has(row.value?.toLowerCase()), 'Enabled or ambiguous worktree configuration is refused');
        } else if (row.section === 'extensions') {
            assert.ok(row.key === 'objectformat' && row.value === 'sha1', 'Unsupported Git repository extension');
        }
        if (row.section === 'core' && row.key === 'bare') {
            assert.ok(FALSE.has(row.value?.toLowerCase()), 'Bare or ambiguous Git root is refused');
        }
    }
    if (ignoredWorktree !== null) {
        // Admit only the inert sparse-checkout-disable residue, never executable
        // or redirected settings even though this file is disabled by the audit above.
        for (const row of configRows(ignoredWorktree, true)) {
            assert.ok(row.subsection === null
                && ((row.section === 'core' && ['sparsecheckout', 'sparsecheckoutcone', 'bare'].includes(row.key))
                    || (row.section === 'index' && row.key === 'sparse'))
                && FALSE.has(row.value?.toLowerCase()), 'Non-benign ignored worktree configuration is refused');
        }
    }
    return {worktreeConfiguration: 'disabled', ignoredWorktreePresent: ignoredWorktree !== null};
}
