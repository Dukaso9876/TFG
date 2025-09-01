
<template>
  <div class="container mt-4">
    <h1 class="mb-4 text-center text-md-start">Detalle de Adjudicaciones: {{ identificador }}</h1>

    <div v-if="cargando" class="text-center my-4">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Cargando...</span>
      </div>
    </div>
    <div v-else-if="error" class="alert alert-danger alert-dismissible fade show" role="alert">
      {{ error }}
      <button type="button" class="btn-close" @click="error = null" aria-label="Close"></button>
    </div>
    <div v-else-if="adjudicaciones.length > 0">
      <transition-group name="list">
        <div v-for="(adj, index) in adjudicaciones" :key="index" class="card shadow-sm mb-3">
          <div class="card-header bg-light">
            <h3 class="h5 mb-0">Adjudicación {{ index + 1 }}</h3>
          </div>
          <div class="card-body">
            <ul class="list-group list-group-flush">
              <li v-for="(value, key) in adj" :key="key" class="list-group-item">
                <strong>{{ formatColumnName(key) }}:</strong>
                <a v-if="key === 'link_licitacion'" :href="value" target="_blank" class="btn btn-link p-0">Enlace</a>
                <span v-else>{{ value || '-' }}</span>
              </li>
            </ul>
          </div>
        </div>
      </transition-group>
      <div class="mt-4 d-flex flex-column flex-md-row gap-2">
        <button class="btn btn-primary" @click="verDetalleCriterios">Detalle criterios de licitación</button>
        <button class="btn btn-outline-secondary" @click="volver">Volver</button>
      </div>
    </div>
    <p v-else class="text-muted mt-4 text-center">No se encontraron adjudicaciones para este identificador.</p>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DetalleAdjudicacion',
  data() {
    return {
      identificador: this.$route.params.id,
      adjudicaciones: [],
      cargando: false,
      error: null,
    };
  },
  async created() {
    this.cargando = true;
    try {
      const response = await axios.get(`http://localhost:3000/api/adjudicaciones?filtro=${this.identificador}`);
      this.adjudicaciones = response.data.data;
    } catch (error) {
      this.error = 'Error al cargar el detalle: ' + error.message;
    } finally {
      this.cargando = false;
    }
  },
  methods: {
    formatColumnName(name) {
      return name
        .replace(/___/g, ' - ')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
    },
    verDetalleCriterios() {
      this.cargando = true;
      this.$router.push(`/detalle-criterios/${this.identificador}`);
    },
    volver() {
      this.$router.go(-1);
    },
  },
};
</script>

<style scoped>
/* Estilos existentes se mantienen */
</style>