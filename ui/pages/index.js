import Head from 'next/head'
import IndexingPanel from '../components/IndexingPanel'

export default function Home() {
  return (
    <>
      <Head>
        <title>NL-to-SPARQL - Entity Indexing</title>
        <meta name="description" content="Index entities into vector embeddings" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <IndexingPanel />
      </main>
    </>
  )
}

export async function getServerSideProps() {
  return {
    props: {}
  }
}
