import Image from "next/image";
import Link from "next/link";
import {
  BoltIcon,
  BoxIconLine,
  CheckCircleIcon,
  DollarLineIcon,
  PieChartIcon,
} from "@/icons";

const features = [
  {
    title: "Pazaryeri verilerini tek akışta topla",
    description:
      "Trendyol, Hepsiburada ve Amazon kaynaklarından rakip ilanlarını analiz akışı için hazır hale getir.",
    icon: <BoltIcon className="size-6 text-brand-500" />,
  },
  {
    title: "Rakipleri fiyat tehdidine göre sırala",
    description:
      "Güç, agresiflik ve buybox tehdidi sinyallerini kullanarak hangi rakiplerin kritik olduğunu gör.",
    icon: <PieChartIcon className="size-6 text-brand-500" />,
  },
  {
    title: "Açıklanabilir fiyat adayları üret",
    description:
      "Tek bir kara kutu fiyat yerine stratejisi, güveni ve gerekçesi görünen aday fiyatlarla karar ver.",
    icon: <DollarLineIcon className="size-6 text-brand-500" />,
  },
];

const workflow = [
  "Ürün ve satıcı kayıtları",
  "Veri toplama",
  "Rakip analizi",
  "Fiyat önerisi",
];

export default function FeraSetLanding() {
  return (
    <main className="min-h-screen bg-white text-gray-900 dark:bg-gray-950 dark:text-white">
      <header className="sticky top-0 z-50 border-b border-gray-100 bg-white/90 backdrop-blur dark:border-white/10 dark:bg-gray-950/90">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-7">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/images/logo/logo.svg"
              alt="feraSet"
              width={154}
              height={32}
              className="dark:hidden"
              priority
            />
            <Image
              src="/images/logo/logo-dark.svg"
              alt="feraSet"
              width={154}
              height={32}
              className="hidden dark:block"
              priority
            />
          </Link>

          <nav className="hidden items-center gap-7 text-sm font-medium text-gray-600 dark:text-gray-300 md:flex">
            <a href="#features" className="hover:text-brand-500">
              Özellikler
            </a>
            <a href="#workflow" className="hover:text-brand-500">
              Akış
            </a>
            <a href="#start" className="hover:text-brand-500">
              Başla
            </a>
          </nav>

          <Link
            href="/signin"
            className="inline-flex h-10 items-center justify-center rounded-full bg-brand-500 px-5 text-sm font-medium text-white transition hover:bg-brand-600"
          >
            Giriş Yap
          </Link>
        </div>
      </header>

      <section className="relative overflow-hidden">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 py-16 sm:px-7 lg:grid-cols-[0.95fr_1.05fr] lg:py-24">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-medium text-brand-700 dark:border-brand-500/20 dark:bg-brand-500/10 dark:text-brand-300">
              <CheckCircleIcon className="size-4" />
              E-ticaret fiyat karar merkezi
            </div>
            <h1 className="max-w-3xl text-4xl font-bold leading-tight text-gray-900 dark:text-white sm:text-5xl lg:text-6xl">
              feraSet ile rakip verisini fiyat kararına dönüştür.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-gray-600 dark:text-gray-300">
              Pazaryerlerinden veri topla, rakiplerini skorla ve açıklanabilir
              fiyat önerileriyle operasyon ekibinin karar sürecini hızlandır.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/signup"
                className="inline-flex h-12 items-center justify-center rounded-full bg-brand-500 px-6 text-sm font-semibold text-white shadow-theme-md transition hover:bg-brand-600"
              >
                Şirket Hesabı Oluştur
              </Link>
              <a
                href="#workflow"
                className="inline-flex h-12 items-center justify-center rounded-full border border-gray-300 px-6 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-white/15 dark:text-gray-200 dark:hover:bg-white/5"
              >
                Akışı İncele
              </a>
            </div>
          </div>

          <div className="relative">
            <div className="rounded-[28px] border border-gray-200 bg-white p-3 shadow-theme-xl dark:border-white/10 dark:bg-white/[0.03]">
              <Image
                src="/images/landing/hero-dashboard.jpg"
                alt="feraSet fiyat zeka paneli"
                width={966}
                height={552}
                className="aspect-[16/10] w-full rounded-2xl object-cover"
                priority
              />
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="bg-gray-50 px-5 py-16 dark:bg-white/[0.02] sm:px-7">
        <div className="mx-auto max-w-7xl">
          <div className="mb-10 max-w-2xl">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Projenin backend servislerine hazır karşılama ekranı
            </h2>
            <p className="mt-3 text-sm leading-6 text-gray-600 dark:text-gray-300">
              Bu sayfa kullanıcıyı doğrudan dashboard'a atmak yerine ürün,
              rakip ve fiyat önerisi akışını kısaca anlatır.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-lg border border-gray-200 bg-white p-6 shadow-theme-xs dark:border-white/10 dark:bg-white/[0.03]"
              >
                <div className="mb-5 flex size-12 items-center justify-center rounded-lg bg-brand-50 dark:bg-brand-500/10">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {feature.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-gray-600 dark:text-gray-300">
                  {feature.description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="workflow" className="px-5 py-16 sm:px-7">
        <div className="mx-auto max-w-7xl rounded-lg border border-gray-200 bg-white p-6 dark:border-white/10 dark:bg-white/[0.03] lg:p-8">
          <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                Veri toplamadan öneriyi uygulamaya kadar tek panel.
              </h2>
              <p className="mt-4 text-sm leading-6 text-gray-600 dark:text-gray-300">
                feraSet dashboard'u mevcut API, agent ve data ingestion
                servislerini aynı operasyon ekranında birleştirir.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-4">
              {workflow.map((item, index) => (
                <div
                  key={item}
                  className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-white/10 dark:bg-gray-900"
                >
                  <span className="text-xs font-semibold text-brand-500">
                    0{index + 1}
                  </span>
                  <p className="mt-3 text-sm font-semibold text-gray-900 dark:text-white">
                    {item}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="start" className="px-5 pb-16 sm:px-7">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-5 rounded-lg bg-gray-900 p-6 text-white dark:bg-brand-500 lg:flex-row lg:items-center lg:p-8">
          <div>
            <h2 className="text-2xl font-bold">Analiz paneline geçmeye hazır mısın?</h2>
            <p className="mt-2 text-sm text-white/70">
              Şirket ve ürün kayıtlarını oluştur, veri toplama akışını başlat ve
              fiyat önerilerini yönet.
            </p>
          </div>
          <Link
            href="/signin"
            className="inline-flex h-12 shrink-0 items-center justify-center rounded-full bg-white px-6 text-sm font-semibold text-gray-900 transition hover:bg-gray-100"
          >
            Panele Giriş Yap
          </Link>
        </div>
      </section>
    </main>
  );
}
