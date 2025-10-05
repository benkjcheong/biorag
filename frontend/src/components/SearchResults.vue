<template>
  <div>
    <div v-if="loading" class="loading">
      Searching knowledge graph and documents...
    </div>
    
    <div v-if="summary" class="summary-card">
      <h3>Summary</h3>
      <p>{{ summary }}</p>
    </div>
    
    <div v-if="results.length > 0" class="results">
      <div v-for="result in results" :key="result.pmc_id" class="result-card">
        <div class="result-content">
          <h4>{{ result.title }}</h4>
          <div class="result-meta">
            <span class="authors">{{ result.authors || 'Unknown Authors' }} ({{ result.year }})</span>
            <span class="separator">•</span>
            <span class="journal">{{ result.journal }}</span>
            <span class="separator">•</span>
            <a :href="`https://pmc.ncbi.nlm.nih.gov/articles/${result.pmc_id}/`" target="_blank" class="pmc-id">{{ result.pmc_id }}</a>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="!loading && results.length === 0 && searched" class="no-results">
      No results found. Try different search terms.
    </div>
  </div>
</template>

<script>
export default {
  name: 'SearchResults',
  props: {
    results: Array,
    summary: String,
    loading: Boolean,
    searched: Boolean
  }
}
</script>

<style scoped>
.loading, .no-results {
  text-align: center;
  color: #666;
  padding: 20px;
}

.summary-card {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #007cba;
}

.summary-card h3 {
  margin: 0 0 10px 0;
  color: #1a365d;
}

.results {
  display: grid;
  gap: 15px;
}

.result-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.result-content h4 {
  margin: 0 0 10px 0;
  color: #1a365d;
  line-height: 1.3;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  font-size: 14px;
}

.authors {
  font-weight: 500;
}

.journal {
  font-style: italic;
}

.separator {
  color: #ccc;
}

.pmc-id {
  color: #007cba;
  font-weight: 500;
  text-decoration: none;
}

.pmc-id:hover {
  text-decoration: underline;
}
</style>