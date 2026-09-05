import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { useAuthStore } from './stores/useAuthStore'
import { useFavoritesStore } from './stores/useFavoritesStore'

// Load favorites if user is already logged in (persisted session)
if (useAuthStore.getState().user) {
  useFavoritesStore.getState().loadFavorites()
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />,
)
