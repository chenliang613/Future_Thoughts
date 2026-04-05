const { createApp, ref, computed, watch, nextTick, onUnmounted } = Vue

// Configure marked options
marked.setOptions({
  breaks: true,
  gfm: true,
})

createApp({
  setup() {
    // ─── State ────────────────────────────────────────────
    const projects = ref([])
    const currentProject = ref(null)
    const currentChapter = ref(null)
    const editorContent = ref('')
    const editorMode = ref('split')
    const isDirty = ref(false)

    // Search
    const searchTab = ref('local')
    const searchQuery = ref('')
    const searchResults = ref([])
    const isSearching = ref(false)
    const hasSearched = ref(false)
    const searchError = ref('')

    // AI
    const aiContext = ref('')
    const isGenerating = ref(false)
    const aiPreviewContent = ref('')

    // UI Modals
    const showImportModal = ref(false)
    const showNewProjectModal = ref(false)
    const showAddChapter = ref(false)
    const showAddTag = ref(false)
    const isImporting = ref(false)

    // Form fields
    const newProjectTitle = ref('')
    const newProjectDesc = ref('')
    const newChapterTitle = ref('')
    const newChapterLevel = ref(2)
    const newTag = ref('')

    // Toast
    const toastMsg = ref('')
    const toastType = ref('info')
    let toastTimer = null

    // Sortable instance
    let sortableInstance = null

    // Refs
    const fileInput = ref(null)
    const tagInput = ref(null)

    // ─── Computed ─────────────────────────────────────────
    const sortedChapters = computed(() => {
      if (!currentProject.value) return []
      return [...currentProject.value.chapters].sort((a, b) => a.order - b.order)
    })

    const renderedPreview = computed(() => {
      try {
        return marked.parse(editorContent.value || '')
      } catch {
        return '<em>预览渲染失败</em>'
      }
    })

    // ─── Watchers ─────────────────────────────────────────
    watch(editorContent, () => {
      isDirty.value = true
    })

    // ─── Toast ────────────────────────────────────────────
    function showToast(msg, type = 'info', duration = 2500) {
      toastMsg.value = msg
      toastType.value = type
      clearTimeout(toastTimer)
      toastTimer = setTimeout(() => { toastMsg.value = '' }, duration)
    }

    // ─── API Helpers ──────────────────────────────────────
    async function apiFetch(url, options = {}) {
      const res = await fetch(url, options)
      if (!res.ok) {
        let msg = `请求失败 (${res.status})`
        try {
          const err = await res.json()
          msg = err.detail || msg
        } catch {}
        throw new Error(msg)
      }
      return res
    }

    async function apiJSON(url, options = {}) {
      const res = await apiFetch(url, options)
      return res.json()
    }

    // ─── Projects ─────────────────────────────────────────
    async function loadProjects() {
      try {
        projects.value = await apiJSON('/api/projects')
      } catch (e) {
        showToast('加载报告列表失败：' + e.message, 'error')
      }
    }

    async function selectProject(id) {
      if (isDirty.value && currentChapter.value) {
        await saveChapter()
      }
      try {
        currentProject.value = await apiJSON(`/api/projects/${id}`)
        currentChapter.value = null
        editorContent.value = ''
        isDirty.value = false
      } catch (e) {
        showToast('加载报告失败：' + e.message, 'error')
      }
    }

    async function createProject() {
      const title = newProjectTitle.value.trim()
      if (!title) return
      try {
        const project = await apiJSON('/api/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, description: newProjectDesc.value }),
        })
        showNewProjectModal.value = false
        newProjectTitle.value = ''
        newProjectDesc.value = ''
        await loadProjects()
        await selectProject(project.id)
        showToast('报告创建成功', 'success')
      } catch (e) {
        showToast('创建失败：' + e.message, 'error')
      }
    }

    async function confirmDeleteProject(p) {
      if (!confirm(`确认删除报告"${p.title}"？此操作不可恢复。`)) return
      try {
        await apiFetch(`/api/projects/${p.id}`, { method: 'DELETE' })
        if (currentProject.value && currentProject.value.id === p.id) {
          currentProject.value = null
          currentChapter.value = null
          editorContent.value = ''
          isDirty.value = false
        }
        await loadProjects()
        showToast('报告已删除', 'info')
      } catch (e) {
        showToast('删除失败：' + e.message, 'error')
      }
    }

    // ─── Import ───────────────────────────────────────────
    function handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) importMd(file)
    }

    function handleFileDrop(event) {
      const file = event.dataTransfer.files[0]
      if (file && file.name.endsWith('.md')) importMd(file)
    }

    async function importMd(file) {
      isImporting.value = true
      try {
        const formData = new FormData()
        formData.append('file', file)
        // Do NOT set Content-Type — browser sets it with boundary
        const project = await apiJSON('/api/import', { method: 'POST', body: formData })
        showImportModal.value = false
        await loadProjects()
        await selectProject(project.id)
        showToast(`导入成功：解析出 ${project.chapters.length} 个章节`, 'success')
      } catch (e) {
        showToast('导入失败：' + e.message, 'error')
      } finally {
        isImporting.value = false
        // Reset file input
        if (fileInput.value) fileInput.value.value = ''
      }
    }

    // ─── Export ───────────────────────────────────────────
    async function exportProject() {
      if (!currentProject.value) return
      if (isDirty.value && currentChapter.value) {
        await saveChapter()
      }
      const a = document.createElement('a')
      a.href = `/api/export/${currentProject.value.id}`
      a.click()
      showToast('报告已导出', 'success')
    }

    // ─── Chapters ─────────────────────────────────────────
    function selectChapter(chapter) {
      if (currentChapter.value && currentChapter.value.id === chapter.id) return
      if (isDirty.value) {
        saveChapter()
      }
      currentChapter.value = chapter
      editorContent.value = chapter.content || ''
      isDirty.value = false
      showAddTag.value = false
    }

    async function saveChapter() {
      if (!currentChapter.value || !currentProject.value) return
      try {
        await apiJSON(
          `/api/chapters/${currentProject.value.id}/${currentChapter.value.id}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: editorContent.value }),
          }
        )
        isDirty.value = false
        // Update local cache
        const ch = currentProject.value.chapters.find(c => c.id === currentChapter.value.id)
        if (ch) ch.content = editorContent.value
        showToast('已保存', 'success', 1500)
      } catch (e) {
        showToast('保存失败：' + e.message, 'error')
      }
    }

    async function addChapter() {
      const title = newChapterTitle.value.trim()
      if (!title || !currentProject.value) return
      try {
        const updated = await apiJSON(`/api/chapters/${currentProject.value.id}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, level: newChapterLevel.value }),
        })
        currentProject.value = updated
        showAddChapter.value = false
        newChapterTitle.value = ''
        newChapterLevel.value = 2
        // Select new chapter
        const newCh = updated.chapters[updated.chapters.length - 1]
        selectChapter(newCh)
        showToast('章节已添加', 'success')
      } catch (e) {
        showToast('添加失败：' + e.message, 'error')
      }
    }

    async function confirmDeleteChapter(chapter) {
      if (!confirm(`确认删除章节"${chapter.title}"？`)) return
      try {
        const updated = await apiJSON(
          `/api/chapters/${currentProject.value.id}/${chapter.id}`,
          { method: 'DELETE' }
        )
        currentProject.value = updated
        if (currentChapter.value && currentChapter.value.id === chapter.id) {
          currentChapter.value = null
          editorContent.value = ''
          isDirty.value = false
        }
        showToast('章节已删除', 'info')
      } catch (e) {
        showToast('删除失败：' + e.message, 'error')
      }
    }

    // ─── Tags ─────────────────────────────────────────────
    function openAddTag() {
      showAddTag.value = true
      nextTick(() => {
        if (tagInput.value) tagInput.value.focus()
      })
    }

    async function addTag() {
      const tag = newTag.value.trim()
      if (!tag || !currentChapter.value) return
      const tags = [...(currentChapter.value.tags || []), tag]
      try {
        await apiJSON(
          `/api/chapters/${currentProject.value.id}/${currentChapter.value.id}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags }),
          }
        )
        currentChapter.value.tags = tags
        newTag.value = ''
        showAddTag.value = false
      } catch (e) {
        showToast('添加标签失败：' + e.message, 'error')
      }
    }

    async function removeTag(tag) {
      if (!currentChapter.value) return
      const tags = currentChapter.value.tags.filter(t => t !== tag)
      try {
        await apiJSON(
          `/api/chapters/${currentProject.value.id}/${currentChapter.value.id}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags }),
          }
        )
        currentChapter.value.tags = tags
      } catch (e) {
        showToast('移除标签失败：' + e.message, 'error')
      }
    }

    // ─── Sortable.js Reorder ──────────────────────────────
    function initSortable() {
      nextTick(() => {
        const el = document.getElementById('chapter-list')
        if (!el) return
        if (sortableInstance) {
          sortableInstance.destroy()
          sortableInstance = null
        }
        sortableInstance = Sortable.create(el, {
          animation: 150,
          handle: '.chapter-drag',
          ghostClass: 'chapter-ghost',
          onEnd: async (evt) => {
            if (evt.oldIndex === evt.newIndex) return
            const ids = sortedChapters.value.map(c => c.id)
            const [moved] = ids.splice(evt.oldIndex, 1)
            ids.splice(evt.newIndex, 0, moved)
            // Optimistically update local order to prevent flicker
            ids.forEach((id, i) => {
              const ch = currentProject.value.chapters.find(c => c.id === id)
              if (ch) ch.order = i
            })
            try {
              const updated = await apiJSON(`/api/reorder/${currentProject.value.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chapter_ids: ids }),
              })
              updated.chapters.forEach(uc => {
                const local = currentProject.value.chapters.find(c => c.id === uc.id)
                if (local) local.order = uc.order
              })
            } catch (e) {
              showToast('排序失败：' + e.message, 'error')
              // Reload to restore correct order
              currentProject.value = await apiJSON(`/api/projects/${currentProject.value.id}`)
              initSortable()
            }
          }
        })
      })
    }

    // Reinit when project switches
    watch(() => currentProject.value?.id, (newId) => {
      if (newId) initSortable()
      else if (sortableInstance) { sortableInstance.destroy(); sortableInstance = null }
    })

    // Reinit when chapters are added or removed
    watch(() => currentProject.value?.chapters?.length, () => {
      if (currentProject.value) initSortable()
    })

    onUnmounted(() => {
      if (sortableInstance) sortableInstance.destroy()
    })

    // ─── Search ───────────────────────────────────────────
    async function runSearch() {
      const q = searchQuery.value.trim()
      if (!q) return
      isSearching.value = true
      hasSearched.value = true
      searchResults.value = []
      searchError.value = ''
      try {
        if (searchTab.value === 'local') {
          const data = await apiJSON(`/api/search/local?q=${encodeURIComponent(q)}`)
          searchResults.value = data.results
        } else if (searchTab.value === 'web') {
          const data = await apiJSON(`/api/search/web?q=${encodeURIComponent(q)}`)
          searchResults.value = data.results
        }
      } catch (e) {
        searchError.value = e.message
      } finally {
        isSearching.value = false
      }
    }

    // Navigate to local search result
    async function navigateToResult(result) {
      if (!currentProject.value || currentProject.value.id !== result.project_id) {
        await selectProject(result.project_id)
      }
      const chapter = currentProject.value.chapters.find(c => c.id === result.chapter_id)
      if (chapter) selectChapter(chapter)
    }

    // Insert web reference into editor
    function insertWebRef(result) {
      if (!currentChapter.value) {
        showToast('请先选择一个章节', 'error')
        return
      }
      editorContent.value += `\n\n- [${result.title}](${result.url})`
      isDirty.value = true
      showToast('引用已插入编辑器', 'success')
    }

    // ─── AI Generation ────────────────────────────────────
    async function generateAiContent() {
      if (!currentChapter.value || !currentProject.value) {
        showToast('请先选择章节', 'error')
        return
      }
      isGenerating.value = true
      aiPreviewContent.value = ''
      searchError.value = ''
      try {
        const data = await apiJSON('/api/ai/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: currentProject.value.id,
            chapter_id: currentChapter.value.id,
            context: aiContext.value,
          }),
        })
        aiPreviewContent.value = data.content
      } catch (e) {
        searchError.value = e.message
        showToast('AI生成失败：' + e.message, 'error')
      } finally {
        isGenerating.value = false
      }
    }

    function applyAiContent(mode) {
      if (!aiPreviewContent.value) return
      if (mode === 'append') {
        editorContent.value = editorContent.value.trimEnd() + '\n\n' + aiPreviewContent.value
      } else {
        // Replace: keep heading line if it starts with #
        const lines = editorContent.value.split('\n')
        const headingLine = lines[0] && lines[0].startsWith('#') ? lines[0] + '\n\n' : ''
        editorContent.value = headingLine + aiPreviewContent.value
      }
      isDirty.value = true
      aiPreviewContent.value = ''
      showToast('内容已应用到编辑器', 'success')
    }

    // ─── Init ─────────────────────────────────────────────
    loadProjects()

    return {
      // State
      projects,
      currentProject,
      currentChapter,
      editorContent,
      editorMode,
      isDirty,
      searchTab,
      searchQuery,
      searchResults,
      isSearching,
      hasSearched,
      searchError,
      aiContext,
      isGenerating,
      aiPreviewContent,
      showImportModal,
      showNewProjectModal,
      showAddChapter,
      showAddTag,
      isImporting,
      newProjectTitle,
      newProjectDesc,
      newChapterTitle,
      newChapterLevel,
      newTag,
      toastMsg,
      toastType,
      // Computed
      sortedChapters,
      renderedPreview,
      // Refs
      fileInput,
      tagInput,
      // Methods
      selectProject,
      createProject,
      confirmDeleteProject,
      handleFileSelect,
      handleFileDrop,
      exportProject,
      selectChapter,
      saveChapter,
      addChapter,
      confirmDeleteChapter,
      openAddTag,
      addTag,
      removeTag,
      runSearch,
      navigateToResult,
      insertWebRef,
      generateAiContent,
      applyAiContent,
    }
  }
}).mount('#app')
