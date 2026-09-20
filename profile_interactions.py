import asyncio
import json
import time
from playwright.async_api import async_playwright

async def run_profiler():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Connect to Chrome DevTools Protocol
        cdp = await context.new_cdp_session(page)
        await cdp.send("Performance.enable")
        
        print("\n--- [STAGE 1] Loading Application & Initial Mount ---")
        await page.goto("http://localhost:3000", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Clear initial mount logs so we capture ONLY user interactions
        await page.evaluate("window.__REACT_PROFILER_LOGS__ = [];")

        print("--- [STAGE 2] Starting CDP Performance Tracing & Profiling ---")
        await cdp.send("Tracing.start", {
            "categories": "-*,devtools.timeline,disabled-by-default-devtools.timeline,blink.user_timing,v8.execute",
            "options": "sampling-frequency=10000"
        })

        interaction_metrics = []

        # --- Helper for interaction measurement ---
        async def measure_action(name, action_fn):
            # Record start timestamp
            t0 = time.perf_counter()
            await page.evaluate(f"performance.mark('{name}_start');")
            
            await action_fn()
            
            await page.evaluate(f"performance.mark('{name}_end');")
            await page.evaluate(f"performance.measure('{name}', '{name}_start', '{name}_end');")
            t_total = (time.perf_counter() - t0) * 1000
            
            # Fetch latest react profiler logs
            logs = await page.evaluate("window.__REACT_PROFILER_LOGS__ || [];")
            await page.evaluate("window.__REACT_PROFILER_LOGS__ = [];")
            
            return {
                "action": name,
                "total_wall_clock_ms": round(t_total, 2),
                "react_components_rendered": logs
            }

        # 1. Click Scenario Card 2 (Enterprise Dispute)
        print("Profiling Interaction 1: Click Scenario Card 'Enterprise Dispute'...")
        metric1 = await measure_action(
            "click_scenario_enterprise", 
            lambda: page.click("text=Enterprise Dispute")
        )
        interaction_metrics.append(metric1)
        await page.wait_for_timeout(100)

        # 2. Click Scenario Card 3 (Privilege Escalation)
        print("Profiling Interaction 2: Click Scenario Card 'Privilege Escalation'...")
        metric2 = await measure_action(
            "click_scenario_role_mismatch", 
            lambda: page.click("text=Privilege Escalation")
        )
        interaction_metrics.append(metric2)
        await page.wait_for_timeout(100)

        # 3. Click Scenario Card 1 (VIP Priority Refund)
        print("Profiling Interaction 3: Click Scenario Card 'VIP Priority Refund'...")
        metric3 = await measure_action(
            "click_scenario_vip_refund", 
            lambda: page.click("text=VIP Priority Refund")
        )
        interaction_metrics.append(metric3)
        await page.wait_for_timeout(100)

        # 4. Drag Slider
        print("Profiling Interaction 4: Drag Ceiling Slider...")
        slider = await page.query_selector('input[type="range"]')
        if slider:
            box = await slider.bounding_box()
            async def drag_slider():
                # Drag smoothly across 4 positions
                for frac in [0.3, 0.5, 0.7, 0.9]:
                    await page.mouse.click(box["x"] + box["width"] * frac, box["y"] + box["height"] / 2)
                    await page.wait_for_timeout(25)
            metric4 = await measure_action("drag_slider_range", drag_slider)
            interaction_metrics.append(metric4)
        await page.wait_for_timeout(100)

        # 5. Switch Tab to Architecture
        print("Profiling Interaction 5: Switch Tab to 'Architecture'...")
        metric5 = await measure_action(
            "switch_tab_architecture", 
            lambda: page.click("button:has-text('Architecture')")
        )
        interaction_metrics.append(metric5)
        await page.wait_for_timeout(100)

        # 6. Click Architecture Node 1 (AgentCore Gateway)
        print("Profiling Interaction 6: Click Architecture Node 'AgentCore Gateway'...")
        metric6 = await measure_action(
            "click_arch_node_gateway", 
            lambda: page.click("text=AgentCore Gateway")
        )
        interaction_metrics.append(metric6)
        await page.wait_for_timeout(100)

        # 7. Click Architecture Node 5 (Bedrock & Engine)
        print("Profiling Interaction 7: Click Architecture Node 'Bedrock & Engine'...")
        metric7 = await measure_action(
            "click_arch_node_bedrock", 
            lambda: page.click("text=Bedrock & Engine")
        )
        interaction_metrics.append(metric7)
        await page.wait_for_timeout(100)

        # 8. Click Architecture Node 6 (DynamoDB Ledger)
        print("Profiling Interaction 8: Click Architecture Node 'DynamoDB Ledger'...")
        metric8 = await measure_action(
            "click_arch_node_dynamodb", 
            lambda: page.click("text=DynamoDB Ledger")
        )
        interaction_metrics.append(metric8)
        await page.wait_for_timeout(100)

        # Stop CDP Tracing
        trace_events = []
        cdp.on("Tracing.dataCollected", lambda e: trace_events.extend(e.get("value", [])))
        await cdp.send("Tracing.end")
        await asyncio.sleep(0.5)

        # Browser Performance Entries
        perf_data = await page.evaluate("""() => {
            return {
                measures: performance.getEntriesByType('measure').map(m => ({
                    name: m.name,
                    duration_ms: Number(m.duration.toFixed(2)),
                    startTime_ms: Number(m.startTime.toFixed(2))
                })),
                network_resources: performance.getEntriesByType('resource').map(r => ({
                    name: r.name,
                    type: r.initiatorType,
                    duration_ms: Number(r.duration.toFixed(2))
                }))
            };
        }""")

        # Categorize CDP trace timings
        cdp_breakdown = {
            "JavaScript Execution (Script/V8/Callbacks)": 0.0,
            "Recalculate Styles (CSS Rule Matching)": 0.0,
            "Layout / Reflow (DOM Geometry)": 0.0,
            "PrePaint & Paint (Rasterization)": 0.0,
            "Composite Layers (GPU Compositor)": 0.0,
        }

        for ev in trace_events:
            dur = ev.get("dur", 0) / 1000.0  # ms
            name = ev.get("name", "")
            if name in ["EvaluateScript", "FunctionCall", "v8.compile", "EventDispatch", "FireAnimationFrame"]:
                cdp_breakdown["JavaScript Execution (Script/V8/Callbacks)"] += dur
            elif name in ["UpdateLayoutTree", "RecalculateStyles"]:
                cdp_breakdown["Recalculate Styles (CSS Rule Matching)"] += dur
            elif name in ["Layout"]:
                cdp_breakdown["Layout / Reflow (DOM Geometry)"] += dur
            elif name in ["Paint", "PrePaint", "RasterTask"]:
                cdp_breakdown["PrePaint & Paint (Rasterization)"] += dur
            elif name in ["CompositeLayers"]:
                cdp_breakdown["Composite Layers (GPU Compositor)"] += dur

        # Format output
        report = {
            "session_summary": "CedarShield Interactive Profiling Run",
            "interaction_profiling_results": interaction_metrics,
            "browser_user_timing_measures": perf_data["measures"],
            "cdp_trace_timeline_breakdown_ms": {k: round(v, 2) for k, v in cdp_breakdown.items()},
            "network_requests_during_interactions": [
                r for r in perf_data["network_resources"] if r["type"] in ["fetch", "xmlhttprequest"]
            ]
        }

        with open("profiling_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print("\n================================================================================")
        print("EMPIRICAL PROFILING REPORT")
        print("================================================================================")
        print(json.dumps(report, indent=2))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_profiler())
