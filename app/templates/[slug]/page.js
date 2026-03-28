import { redirect } from "next/navigation";

export default function TemplateDetailPage({ params }) {
  redirect(`/market/${params.slug}`);
}
