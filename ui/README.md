# NL-to-SPARQL Web UI

React/Next.js frontend for the Natural Language to SPARQL system.

## Features

- 🔍 **Entity Indexing UI** - Select SPARQL endpoint and trigger indexing
- 📊 **Status Display** - Real-time progress and feedback
- ⚡ **Quick Select** - Pre-configured endpoints (DBpedia, Wikidata, Localhost)
- 🎨 **Beautiful UI** - Modern, responsive design with gradient backgrounds

## Installation

### 1. Install dependencies

```bash
cd ui
npm install
```

### 2. Run development server

```bash
npm run dev
```

The UI will be available at `http://localhost:3000`

## Configuration

The frontend expects the backend API to be running on `http://localhost:8000`. This is configured in `next.config.js` with rewrites.

If your backend is running on a different port, update `next.config.js`:

```javascript
rewrites: async () => {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:YOUR_PORT/api/:path*'
    }
  ]
}
```

## Usage

1. **Select an endpoint** - Click one of the quick select buttons or paste a custom URL
2. **Click "Index"** - Start the indexing pipeline
3. **Watch the progress** - Monitor the status in real-time
4. **Verify completion** - Check the success/error status

## Components

- **IndexingPanel** - Main component with form, status display, and info
- **CSS Modules** - Scoped styling for component isolation

## Building for production

```bash
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file if you need custom configuration:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then use in components:

```javascript
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

## Troubleshooting

**CORS errors?** Make sure the backend has CORS enabled. Check `api/main.py`.

**API not responding?** Verify the backend is running: `python main.py api`

**Port already in use?** Use a different port: `npm run dev -- -p 3001`
