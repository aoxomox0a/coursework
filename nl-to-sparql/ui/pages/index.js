import Head from 'next/head'
import QueryTranslator from '../components/QueryTranslator'

export default function Home() {
  return (
    <>
      <Head>
        <title>NL-to-SPARQL - Query Translator</title>
        <meta name="description" content="Translate natural language to SPARQL queries" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <QueryTranslator />
      </main>
    </>
  )
}

export async function getServerSideProps() {
  return {
    props: {}
  }
}
