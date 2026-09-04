import { MapPin, Phone, Mail } from "lucide-react";

const quickLinks = [
  { label: "About Us", href: "#about" },
  { label: "Departments", href: "#departments" },
  { label: "Placements", href: "#placements" },
  { label: "Contact Us", href: "#footer" },
];

const Footer = () => {
  return (
    <footer id="footer" className="bg-primary text-primary-foreground">
      <div className="container mx-auto px-4 py-16">
        <div className="grid gap-12 md:grid-cols-2">
          <div>
            <h3 className="mb-4 font-display text-xl font-bold">
              Nadimpalli Satyanarayana Raju Institute Of Technology
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-primary-foreground/70">
              Empowering students with quality education and industry-ready skills.
              Approved by AICTE and affiliated to the University.
            </p>
            <div className="flex flex-col gap-2 text-sm text-primary-foreground/70">
              <span className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-accent" />
                Visakhapatnam, Andhra Pradesh
              </span>
              <span className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-accent" />
                +91 9876543210
              </span>
              <span className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-accent" />
                nsrit@college.edu.in
              </span>
            </div>
          </div>

          <div>
            <h3 className="mb-4 font-display text-lg font-bold">Quick Links</h3>
            <ul className="space-y-2 text-sm text-primary-foreground/70">
              {quickLinks.map((link) => (
                <li key={link.label}>
                  <a href={link.href} className="transition-colors hover:text-accent">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="border-t border-primary-foreground/10 py-4">
        <p className="text-center text-sm text-primary-foreground/50">
          © 2008 Nadimpalli Satyanarayana Raju Institute Of Technology. All rights reserved.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
