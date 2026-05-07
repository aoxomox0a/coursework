import '../styles/globals.css'
import { StatusProvider } from '../context/StatusContext';

function MyApp({ Component, pageProps }) {
  return (
    <StatusProvider>
      <Component {...pageProps} />
    </StatusProvider>
  );
}

export default MyApp;
