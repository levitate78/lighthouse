/**
 * main.js — Vite entry point.
 *
 * Import order matters: CSS first so it's extracted into a separate chunk
 * by Vite's build, then the application bootstrap.
 */

import '../src/css/main.css'
import './app.js'