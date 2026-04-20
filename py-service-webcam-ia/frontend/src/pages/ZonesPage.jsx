import ZonesEditor from '../components/ZonesEditor'

export default function ZonesPage({ payload, onChange, state }) {
  return <ZonesEditor payload={payload} onChange={onChange} preview={state?.latest_preview_b64} />
}
