<template>
  <div class="markdown-body" v-html="rendered"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import DOMPurify from 'dompurify'
import 'highlight.js/styles/atom-one-dark.css'

// Register only the commonly used languages to keep the bundle small
import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import css from 'highlight.js/lib/languages/css'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import go from 'highlight.js/lib/languages/go'
import ini from 'highlight.js/lib/languages/ini'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import php from 'highlight.js/lib/languages/php'
import python from 'highlight.js/lib/languages/python'
import ruby from 'highlight.js/lib/languages/ruby'
import rust from 'highlight.js/lib/languages/rust'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

const languages = {
  bash, c, cpp, css, dockerfile, go, ini, java, javascript, json,
  markdown, php, python, ruby, rust, sql, typescript, xml, yaml,
}
Object.entries(languages).forEach(([name, lang]) => hljs.registerLanguage(name, lang))

// Markdown -> HTML with syntax highlighting (marked v12 renderer API)
const renderer = new marked.Renderer()
renderer.code = ({ text, lang }) => {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  let highlighted
  try {
    highlighted = hljs.highlight(text, { language }).value
  } catch {
    highlighted = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
  const label = lang ? lang : 'text'
  return (
    `<div class="code-block"><div class="code-lang">${label}</div>` +
    `<pre><code class="hljs language-${label}">${highlighted}</code></pre></div>`
  )
}
marked.use({ renderer, breaks: true, gfm: true })

const props = defineProps({
  content: { type: String, default: '' },
})

const rendered = computed(() => {
  if (!props.content) return ''
  const html = marked.parse(props.content, { async: false })
  return DOMPurify.sanitize(html)
})
</script>

<style scoped>
.markdown-body {
  font-size: 0.92rem;
  line-height: 1.75;
  word-break: break-word;
}
.markdown-body :deep(p) {
  margin: 0.35em 0;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 0.9em 0 0.4em;
  font-weight: 600;
  line-height: 1.4;
}
.markdown-body :deep(h1) {
  font-size: 1.25rem;
}
.markdown-body :deep(h2) {
  font-size: 1.12rem;
}
.markdown-body :deep(h3) {
  font-size: 1.02rem;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.4em;
}
.markdown-body :deep(li) {
  margin: 0.2em 0;
}
.markdown-body :deep(a) {
  color: #818cf8;
  text-decoration: underline;
}
.markdown-body :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.2em 1em;
  border-left: 3px solid rgba(99, 102, 241, 0.6);
  color: #94a3b8;
  background: rgba(99, 102, 241, 0.06);
  border-radius: 0 8px 8px 0;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 0.6em 0;
  width: 100%;
  font-size: 0.85em;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid rgba(148, 163, 184, 0.3);
  padding: 0.4em 0.7em;
  text-align: left;
}
.markdown-body :deep(th) {
  background: rgba(148, 163, 184, 0.12);
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid rgba(148, 163, 184, 0.3);
  margin: 0.9em 0;
}
.markdown-body :deep(code):not(.hljs) {
  padding: 0.15em 0.4em;
  border-radius: 6px;
  font-size: 0.85em;
  background: rgba(99, 102, 241, 0.14);
  color: #c7d2fe;
}
html:not(.dark) .markdown-body :deep(code):not(.hljs) {
  background: rgba(99, 102, 241, 0.12);
  color: #4f46e5;
}
.markdown-body :deep(.code-block) {
  margin: 0.6em 0;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #282c34;
}
.markdown-body :deep(.code-lang) {
  padding: 4px 12px;
  font-size: 0.7rem;
  color: #abb2bf;
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.markdown-body :deep(pre) {
  margin: 0;
  padding: 12px 14px;
  overflow-x: auto;
}
.markdown-body :deep(pre code) {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;
  font-size: 0.82rem;
  background: transparent !important;
  padding: 0;
}
</style>
