export default function RegisterPage() {
  return (
    <main className="page">
      <div className="card" style={{ maxWidth: 520, margin: "0 auto" }}>
        <h1>Create your account</h1>
        <p>Registration maps to <code>/api/v1/auth/register</code> and supports email verification out of the box.</p>
      </div>
    </main>
  );
}
