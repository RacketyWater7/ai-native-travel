export default function ReservePage({ params }: { params: { id: string } }) {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <div className="card p-8 text-center">
        <p className="text-sm uppercase tracking-[0.2em] text-black/50">Mock booking</p>
        <h1 className="mt-3 text-4xl font-black">Reservation confirmed</h1>
        <p className="mt-3 text-black/65">Your demo hold for property #{params.id} is confirmed. No payment was taken.</p>
        <a className="button mt-6 inline-block" href="/">Back to search</a>
      </div>
    </main>
  );
}
