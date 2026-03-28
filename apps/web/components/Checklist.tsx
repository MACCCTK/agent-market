type ChecklistProps = {
  title: string;
  items: Array<{ id: string; description: string }>;
};

export function Checklist({ title, items }: ChecklistProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-3">
            <span className="mt-1 h-2.5 w-2.5 rounded-full bg-brand-500" />
            <p className="text-sm text-slate-700">{item.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
