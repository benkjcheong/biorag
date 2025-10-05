<template>
  <div class="search-box">
    <input 
      v-model="query" 
      @keyup.enter="search"
      class="search-input" 
      placeholder="Search for space biology experiments, effects, organisms..."
    >
    <button @click="search" class="search-btn" :disabled="loading">
      {{ loading ? 'Searching...' : 'Search' }}
    </button>
  </div>
</template>

<script>
export default {
  name: 'SearchBox',
  props: {
    loading: Boolean
  },
  data() {
    return {
      query: ''
    }
  },
  methods: {
    search() {
      if (this.query.trim()) {
        this.$emit('search', this.query)
      }
    }
  }
}
</script>

<style scoped>
.search-box {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.search-btn {
  padding: 12px 24px;
  background: #007cba;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.search-btn:hover:not(:disabled) {
  background: #005a87;
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>