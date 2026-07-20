import Image from "next/image";
import { CREATOR } from "@/config/creator";

const external = { target: "_blank", rel: "noopener noreferrer" } as const;

export default function CreatorStrip() {
  return (
    <section
      aria-label="Follow and support the creator"
      className="mx-auto flex max-w-[1180px] flex-wrap items-center gap-2.5 pb-2.5"
    >
      <a
        href={CREATOR.blog}
        {...external}
        aria-label={`Read ${CREATOR.name}'s blog`}
        className="shrink-0 rounded-full ring-1 ring-gold/35 transition hover:ring-gold"
      >
        <Image
          src={CREATOR.avatar}
          alt={CREATOR.name}
          width={38}
          height={38}
          className="h-[38px] w-[38px] rounded-full object-cover grayscale"
        />
      </a>

      <div className="mr-auto min-w-[180px]">
        <div className="text-[11px] font-medium text-parchment">Follow Shawn, the builder behind the map</div>
        <div className="mt-0.5 text-[9px] text-muted-2">
          Founder&apos;s projects:{" "}
          {CREATOR.projects.map((project, index) => (
            <span key={project.label}>
              <a
                href={project.href}
                {...external}
                title={project.note}
                className="text-muted underline decoration-rope underline-offset-2 transition-colors hover:text-gold"
              >
                {project.label}
              </a>
              {index < CREATOR.projects.length - 1 ? " · " : ""}
            </span>
          ))}
        </div>
      </div>

      <nav aria-label="Shawn's social profiles" className="flex flex-wrap items-center gap-1.5">
        {CREATOR.socials.map((social) => (
          <a
            key={social.label}
            href={social.href}
            {...external}
            aria-label={`${social.label}: ${social.handle}`}
            className="rounded-full border border-rope/70 bg-ink/65 px-2.5 py-1 font-mono text-[9px] text-muted transition-colors hover:border-gold/60 hover:text-gold"
          >
            {social.label}
            <span className="ml-1 hidden text-muted-2 xl:inline">{social.handle}</span>
          </a>
        ))}
        <a
          href={CREATOR.support}
          {...external}
          className="rounded-full border border-gold/55 bg-gold/10 px-2.5 py-1 font-mono text-[9px] text-gold transition-colors hover:border-gold hover:bg-gold/15"
        >
          ☆ Star / support
        </a>
      </nav>
    </section>
  );
}
