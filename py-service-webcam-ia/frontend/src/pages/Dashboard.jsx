import VideoCard from '../components/VideoCard'
import EventList from '../components/EventList'

export default function Dashboard({ state, rules, events }) {
  return (
    <div className="grid-dashboard">
      <VideoCard state={state} rules={rules} />
      <EventList events={events.slice(0, 12)} />
    </div>
  )
}
