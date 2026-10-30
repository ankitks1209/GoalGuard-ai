import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Setup } from './Setup';
import './setup.css';

const root = document.getElementById('root');
export const mountedRoot = root ? createRoot(root) : null;
if (mountedRoot) {
  mountedRoot.render(<StrictMode><Setup /></StrictMode>);
}
