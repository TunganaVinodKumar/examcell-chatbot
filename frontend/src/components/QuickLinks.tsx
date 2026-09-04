import { motion } from "framer-motion";
import { ShieldCheck, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

const QuickLinks = () => {
  return (
    <section className="bg-white px-4 py-14 md:py-16">
      <div className="container mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-5xl overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.12)]"
        >
          <div className="grid gap-0 md:grid-cols-[1.2fr_0.8fr]">
            <div className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 px-8 py-10 text-white md:px-10 md:py-12">
              <div className="mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20">
                <ShieldCheck className="h-7 w-7 text-amber-300" />
              </div>

              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-amber-300">
                Admin Portal
              </p>

              <h2 className="mb-4 font-display text-3xl font-bold leading-tight md:text-4xl">
                Exam Cell Management
              </h2>

              <p className="max-w-xl text-sm leading-7 text-white/80 md:text-base">
                Access the exam cell dashboard to upload circulars, manage the
                knowledge base, and monitor document processing.
              </p>
            </div>

            <div className="flex flex-col justify-center bg-slate-50 px-8 py-10 md:px-10 md:py-12">
              <div className="mb-5">
                <h3 className="text-xl font-semibold text-slate-900">
                  Exam Cell Login
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Authorized staff can continue to the secure dashboard from here.
                </p>
              </div>

              <Link
                to="/examcell-login"
                className="inline-flex w-fit items-center gap-2 rounded-xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Open Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default QuickLinks;
