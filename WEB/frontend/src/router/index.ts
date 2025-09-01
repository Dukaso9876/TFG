import { createRouter, createWebHistory } from 'vue-router';
import TablaDatos from '@/components/TablaDatos.vue'; // Usar alias @
import DetalleAdjudicacion from '@/views/detalleAdjudicacion.vue';
import DetalleCriterios from '@/views/DetalleCriterios.vue';
import DetalleModificados from '@/views/DetalleModificados.vue';

const routes = [
  { path: '/', redirect: '/adjudicaciones' },
  { path: '/adjudicaciones', component: TablaDatos, props: { tabla: 'adjudicaciones' } },
  { path: '/criterios_adjudicacion', component: TablaDatos, props: { tabla: 'criterios_adjudicacion' } },
  { path: '/modificados', component: TablaDatos, props: { tabla: 'modificados' } },
  { path: '/resultados_licitaciones', component: TablaDatos, props: { tabla: 'resultados_licitaciones' } },
  {
  path: '/detalle-adjudicacion/:id',
  name: 'DetalleAdjudicacion',
  component: DetalleAdjudicacion
},
{
  path: '/detalle-criterios/:id',
  name: 'DetalleCriterios',
  component: DetalleCriterios
},
{
  path: '/detalle-modificados/:id',
  name: 'DetalleModificados',
  component: DetalleModificados
}

];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;