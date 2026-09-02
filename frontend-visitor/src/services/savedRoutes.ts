import type { RoutePlan, SavedRoute } from '../types/route'
import { profileRequest } from './profile'

interface DeleteSavedRouteResponse {
  deleted: number
}

export async function fetchSavedRoutes(): Promise<SavedRoute[]> {
  return profileRequest<SavedRoute[]>({ method: 'GET', url: '/api/profile/routes' })
}

export async function saveRoute(route: RoutePlan): Promise<SavedRoute> {
  return profileRequest<SavedRoute>({
    method: 'POST',
    url: '/api/profile/routes',
    data: { ...route, trace_id: route.trace_id || route.traceId || '' },
  })
}

export async function deleteSavedRoute(
  routeId: number,
): Promise<DeleteSavedRouteResponse> {
  return profileRequest<DeleteSavedRouteResponse>({
    method: 'DELETE',
    url: `/api/profile/routes/${routeId}`,
  })
}
