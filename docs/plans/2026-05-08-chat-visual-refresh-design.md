# Chat Visual Refresh Design

**Goal:** Rebalance the `/chat` workspace so the conversation remains the visual focus, the composer feels compact and intentional, and the sidebar stops overpowering the main work area.

**Scope**
- Keep existing chat capability, API contracts, and interaction model unchanged.
- Refresh only the chat workspace presentation in `apps/web`.
- Preserve the existing compact composer behavior that was already being introduced.

**Design Direction**
- Shift the workspace from a "plain admin panel" look toward a calmer command-center feel.
- Reduce the sidebar's visual weight with tighter proportions, softer shadows, and flatter session cards.
- Add hierarchy to the main header with a kicker and subtitle so the oversized title no longer dominates the page.
- Tighten message spacing and bubble widths so the conversation reads like dialogue instead of stacked notices.
- Make the composer feel like a focused control surface: small label, compact helper text, one clear primary action, and a quieter secondary voice action.

**Visual Rules**
- Use one consistent green-led accent system with muted slate neutrals.
- Keep the background atmospheric but subtle through soft gradients rather than heavy glows.
- Prefer restrained elevation and cleaner borders over large shadows.
- Keep mobile behavior intact by preserving the existing one-column fallback.

**Non-Goals**
- No routing changes.
- No backend or contract changes.
- No new chat capabilities, evidence flows, or admin behaviors.
