// SPDX-License-Identifier: Apache-2.0
import React, { useState } from 'react';
import { ethers } from 'ethers';

const ABI = ["function stake() payable"];
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS ?? '';

export default function App() {
  const [amount, setAmount] = useState('');
  const [cid, setCid] = useState('');
  const [proof, setProof] = useState('');

  async function dispatchGitHub() {
    await fetch(`${API_BASE}/dispatch`, { method: 'POST' });
  }

  async function handleStake() {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      return;
    }
    const provider = new ethers.BrowserProvider((window as any).ethereum);
    await provider.send('eth_requestAccounts', []);
    const signer = await provider.getSigner();
    if (CONTRACT_ADDRESS) {
      const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, signer);
      const tx = await contract.stake({ value: ethers.parseEther(amount || '0') });
      await tx.wait();
    }
    const addr = await signer.getAddress();
    await fetch(`${API_BASE}/stake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: addr, amount: Number(amount) })
    });
    await dispatchGitHub();
  }

  async function loadProof() {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      return;
    }
    const provider = new ethers.BrowserProvider((window as any).ethereum);
    await provider.send('eth_requestAccounts', []);
    const signer = await provider.getSigner();
    const addr = await signer.getAddress();
    const res = await fetch(`${API_BASE}/proof/${addr}`);
    if (res.ok) {
      const data = await res.json();
      setCid(data.cid);
      setProof(data.proof ?? '');
    }
  }

  return (
    <div>
      <h1>Stake Tokens</h1>
      <input value={amount} onChange={(e) => setAmount(e.target.value)} />
      <button type="button" onClick={handleStake}>Stake</button>
      <button type="button" onClick={loadProof}>Load Proof</button>
      {cid && <div className="cid">CID: {cid}</div>}
      {proof && <pre className="proof">{proof}</pre>}
    </div>
  );
}
