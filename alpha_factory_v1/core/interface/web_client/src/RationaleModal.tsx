// SPDX-License-Identifier: Apache-2.0
import React from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  docUrl: string;
}

export default function RationaleModal({ open, onClose, docUrl }: Props) {
  if (!open) return null;
  return (
    <div className="modal-overlay fixed inset-0 bg-black/50 flex justify-center pt-[10%]"
      role="dialog" aria-modal="true" aria-label="Score rationale"
      onKeyDown={(event) => { if (event.key === 'Escape') onClose(); }}>
      <div
        className="modal-content bg-white dark:bg-neutral-900 p-5 max-w-[400px] w-80 sm:w-64 max-h-[40vh] overflow-y-auto"
      >
        <p>
          See <a href={docUrl} target="_blank" rel="noopener noreferrer">documentation</a>{' '}
          for the rationale behind these scores.
        </p>
        <button type="button" autoFocus onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
