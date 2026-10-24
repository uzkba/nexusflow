import axios from "axios";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true,
});

let isRefreshing = false;
let queue: Array<() => void> = [];

async function refreshAccessToken(): Promise<void> {
  // Dispara POST vazio. O cookie httpOnly viaja sozinho pelo withCredentials
  await axios.post(
    `${import.meta.env.VITE_API_BASE_URL}/api/auth/refresh`,
    {},
    { withCredentials: true }
  );
}

httpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Evita loop no login/refresh se der erro neles mesmos
    if (
      error.response?.status !== 401 || 
      original._retry || 
      original.url?.includes('/login') ||
      original.url?.includes('/refresh') 
    ) {
      return Promise.reject(error);
    }
    
    original._retry = true;

    if (isRefreshing) {
      return new Promise((resolve) => {
        queue.push(() => resolve(httpClient(original)));
      });
    }

    isRefreshing = true;
    try {
      await refreshAccessToken();
      
      queue.forEach((cb) => cb());
      queue = [];
      
      // Repete a requisição bloqueada
      return httpClient(original);
    } catch (refreshError) {
      queue = [];
      localStorage.removeItem("usuario");
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);