# ADR 0002: Offline compilation

Status: Accepted

Generation, provider calls, repair, preview rendering, and validation occur in a deliberate development build. The game loads already compiled JSON.

The shipped runtime therefore has no Python, model, network, API key, or generator dependency and behaves predictably on player machines.
