document.addEventListener("DOMContentLoaded", () => {
    // ── STATE VARIABLES ──────────────────────────────────────────────────────
    let currentCurrency = "USD";
    
    // Map Flask active_page to the corresponding activeTab
    const activePageToTab = {
        "analiz_paneli": "dashboard",
        "trend_analizi": "trend",
        "kar_tahmini": "predictor-reg",
        "kar_zarar_siniflandirma": "predictor-kz",
        "yon_siniflandirma": "predictor-dir",
        "rakip_analizi": "competitor-analysis",
        "yonetici_paneli": "admin"
    };
    let activeTab = activePageToTab[window.activePage] || "dashboard";

    // Tab Headers for Dashboard UI Title & Subtitle updates
    const tabHeaders = {
        "dashboard": {
            title: "Analiz Paneli",
            desc: "BIST şirketlerinin kur bazlı hibrit model başarıları ve karşılaştırmaları."
        },
        "trend": {
            title: "Sektörel Trend Analizi",
            desc: "Seçilen şirketin çeyreklik finansal kalemlerini etkileşimli grafiklerle inceleyin."
        },
        "predictor-reg": {
            title: "Kâr Tahmini (Regresyon)",
            desc: "Şirketin finansal verilerini düzenleyerek gelecek çeyrek sayısal net kâr tahmini yapın."
        },
        "predictor-kz": {
            title: "Kâr/Zarar Sınıflandırma",
            desc: "Şirket kârının sektör ortalamasının üzerinde kalıp kalmayacağını (Alpha) tahmin edin."
        },
        "predictor-dir": {
            title: "Yön Sınıflandırma",
            desc: "Gelecek dönem net kârının cari döneme göre artıp azalacağını tahmin edin."
        },
        "competitor-analysis": {
            title: "Sektörel Rakip Analizi",
            desc: "Firmaların sektör genelindeki kârlılık pozisyonları ve rakip karşılaştırmaları."
        },
        "admin": {
            title: "Yönetici Paneli",
            desc: "BIST AI sistem mimarisi, veri tabanı özellikleri ve stacking metodolojisi detayları."
        }
    };

    // Chart.js instance for Time Series Trend Analysis
    let trendChart = null;
    let kzTrendChart = null;
    let dirTrendChart = null;

    // ── NAVIGATION SYSTEM ────────────────────────────────────────────────────
    // Multi-Page Application (MPA) mode:
    // Sidebar links function naturally as regular links, and their active state is rendered server-side.

    // ── CURRENCY SELECTION ───────────────────────────────────────────────────
    const currencySelect = document.getElementById("global-currency");
    if (currencySelect) {
        currencySelect.addEventListener("change", (e) => {
            currentCurrency = e.target.value;
            
            // Sync trend currency buttons
            const trendCurrencyBtns = document.querySelectorAll(".btn-currency");
            trendCurrencyBtns.forEach(btn => {
                if (btn.getAttribute("data-currency") === currentCurrency) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });

            if (activeTab === "dashboard") {
                loadJigsawPerformance();
            }
            // Force refresh company data in active prediction tabs if values are set
            triggerSelectedRefresh();
        });
    }

    // Setup Tab Switching for Sektörel Trend Analizi report card tabs
    document.querySelectorAll(".report-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".report-tab-btn").forEach(b => {
                b.classList.remove("active");
                b.style.color = "#94a3b8";
                b.style.borderBottom = "2px solid transparent";
            });
            btn.classList.add("active");
            btn.style.color = "var(--color-blue)";
            btn.style.borderBottom = "2px solid var(--color-blue)";

            const targetTab = btn.getAttribute("data-tab");
            document.querySelectorAll(".report-tab-content").forEach(div => {
                if (div.id === `report-tab-${targetTab}`) {
                    div.style.display = "block";
                } else {
                    div.style.display = "none";
                }
            });
        });
    });

    // Setup Error Highlight Buttons Click Listeners
    ["kz", "dir"].forEach(prefix => {
        const toggleBtn = document.getElementById(`${prefix}-toggle-errors-btn`);
        if (toggleBtn) {
            toggleBtn.addEventListener("click", () => {
                const isActive = toggleBtn.classList.toggle("active");
                const canvasEl = document.getElementById(`${prefix}-trend-line-chart`);
                if (canvasEl) {
                    canvasEl.dataset.highlightErrors = isActive ? "true" : "false";
                    
                    if (isActive) {
                        toggleBtn.style.background = "#ef4444";
                        toggleBtn.style.color = "#ffffff";
                        toggleBtn.style.boxShadow = "0 0 15px rgba(239, 68, 68, 0.4)";
                    } else {
                        toggleBtn.style.background = "rgba(239, 68, 68, 0.1)";
                        toggleBtn.style.color = "#ef4444";
                        toggleBtn.style.boxShadow = "none";
                    }
                    
                    const chartInstance = canvasEl.chartInstance;
                    if (chartInstance) {
                        chartInstance.update();
                    }
                }
            });
        }
    });

    function triggerSelectedRefresh() {
        const tabs = ["kz", "dir"];
        tabs.forEach(prefix => {
            const sectEl = document.getElementById(`${prefix}-sector`);
            const compEl = document.getElementById(`${prefix}-company`);
            if (sectEl && compEl && sectEl.value && compEl.value) {
                runPredict(prefix);
            }
        });
        // Also refresh trend if set
        const trendSectEl = document.getElementById("trend-sector");
        if (trendSectEl && trendSectEl.value) {
            const selectedTrendComp = getSelectedTrendCompanies();
            if (selectedTrendComp.length > 0) {
                loadTrendFeatures();
            }
        }
        // Also refresh regression trend if set
        const regTrendSectEl = document.getElementById("reg-trend-sector");
        const regTrendCompEl = document.getElementById("reg-trend-company");
        if (regTrendSectEl && regTrendCompEl && regTrendSectEl.value && regTrendCompEl.value) {
            updateRegTrendPlot();
        }
        // Also refresh competitor analysis if set
        const compSectEl = document.getElementById("comp-sector");
        const compCompEl = document.getElementById("comp-company");
        if (compSectEl && compCompEl && compSectEl.value && compCompEl.value) {
            const compBtn = document.getElementById("btn-run-comp-analysis");
            if (compBtn) compBtn.click();
        }
    }

    // ── INITIAL DATA LOADING ─────────────────────────────────────────────────
    function cleanSectorName(sectName) {
        if (!sectName) return "";
        const mapping = {
            "SANAYI_VE_IMALAT": "Sanayi ve İmalat",
            "FINANS_VE_YATIRIM": "Finans ve Yatırım",
            "INSAAT_VE_GAYRIMENKUL": "İnşaat ve Gayrimenkul",
            "TEKNOLOJI_VE_HIZMET": "Teknoloji ve Hizmet",
            "ENERJI_VE_HAMMADDE": "Enerji ve Hammadde",
            "GIDA_VE_TARIM": "Gıda ve Tarım",
            "TICARET_VE_PAZARLAMA": "Ticaret ve Pazarlama"
        };
        const key = sectName.toUpperCase().replace(/\uFFFD/g, "");
        if (mapping[key]) return mapping[key];
        
        // Robust fallback matching for any partial/garbled sheet names
        if (key.includes("SANAY")) return "Sanayi ve İmalat";
        if (key.includes("FINANS") || key.includes("FNANS")) return "Finans ve Yatırım";
        if (key.includes("INSAAT") || key.includes("NAAT")) return "İnşaat ve Gayrimenkul";
        if (key.includes("TEKNOLOJ")) return "Teknoloji ve Hizmet";
        if (key.includes("ENERJ")) return "Enerji ve Hammadde";
        if (key.includes("GIDA")) return "Gıda ve Tarım";
        if (key.includes("TICARET") || key.includes("TCARET")) return "Ticaret ve Pazarlama";
        
        return sectName;
    }


    function getSectorDisplayName(sectorCleanName) {
        const companyCounts = {
            "Sanayi ve İmalat": 125,
            "Finans ve Yatırım": 88,
            "İnşaat ve Gayrimenkul": 59,
            "Teknoloji ve Hizmet": 40,
            "Enerji ve Hammadde": 39,
            "Gıda ve Tarım": 24,
            "Ticaret ve Pazarlama": 32
        };
        const count = companyCounts[sectorCleanName];
        if (count) {
            return `${sectorCleanName} (${count} Firma)`;
        }
        return sectorCleanName;
    }

    // Load Sectors list into all select elements on boot
    fetch("/api/sectors")
        .then(res => res.json())
        .then(data => {
            // Fill trend-sector and comp-sector with firm-count labels (no MAPE)
            const plainSelects = ["trend-sector", "comp-sector"];
            plainSelects.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.innerHTML = '<option value="">Sektör Seçin...</option>';
                    data.sectors.forEach(sect => {
                        const opt = document.createElement("option");
                        opt.value = sect;
                        opt.textContent = getSectorDisplayName(cleanSectorName(sect));
                        el.appendChild(opt);
                    });
                }
            });

            // Fill reg-trend-sector with MAPE labels from the regression model
            const regSectEl = document.getElementById("reg-trend-sector");
            if (regSectEl) {
                regSectEl.innerHTML = '<option value="">Sektör Seçin...</option>';
                // First populate with plain names
                data.sectors.forEach(sect => {
                    const opt = document.createElement("option");
                    opt.value = sect;
                    opt.textContent = getSectorDisplayName(cleanSectorName(sect));
                    regSectEl.appendChild(opt);
                });
                // Then fetch MAPE and enrich labels
                fetch(`/api/sector_mape?currency=${encodeURIComponent(currentCurrency)}`)
                    .then(r => r.json())
                    .catch(() => ({ mapes: {} }))
                    .then(mapeData => {
                        const mapeMap = mapeData.mapes || {};
                        regSectEl.innerHTML = '<option value="">Sektör Seçin...</option>';
                        data.sectors.forEach(sect => {
                            const opt = document.createElement("option");
                            opt.value = sect;
                            const baseName = getSectorDisplayName(cleanSectorName(sect));
                            const mape = mapeMap[sect];
                            opt.textContent = mape != null ? `${baseName}  (%${mape} Ort. MAPE Hatası)` : baseName;
                            regSectEl.appendChild(opt);
                        });
                    });
            }

            // Fill kz-sector and dir-sector with classification accuracy labels
            Promise.all([
                fetch(`/api/sector_accuracy?model=kz&currency=${encodeURIComponent(currentCurrency)}`).then(r => r.json()).catch(() => ({accuracies: {}})),
                fetch(`/api/sector_accuracy?model=yon&currency=${encodeURIComponent(currentCurrency)}`).then(r => r.json()).catch(() => ({accuracies: {}}))
            ]).then(([kzAcc, yonAcc]) => {
                ["kz-sector", "dir-sector"].forEach(id => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    const accMap = id === "kz-sector" ? (kzAcc.accuracies || {}) : (yonAcc.accuracies || {});
                    el.innerHTML = '<option value="">Sektör Seçin...</option>';
                    data.sectors.forEach(sect => {
                        const opt = document.createElement("option");
                        opt.value = sect;
                        const baseName = getSectorDisplayName(cleanSectorName(sect));
                        const acc = accMap[sect];
                        opt.textContent = acc != null ? `${baseName}  (%${Math.round(acc)} Ort. Başarı)` : baseName;
                        el.appendChild(opt);
                    });
                });
            });
        })
        .catch(err => console.error("Sektör listesi yükleme hatası:", err));


    // Initialize correct component based on activeTab
    if (activeTab === "dashboard") {
        loadJigsawPerformance();
    } else if (activeTab === "predictor-kz") {
        setupPredictionListeners("kz");
    } else if (activeTab === "predictor-dir") {
        setupPredictionListeners("dir");
    } else if (activeTab === "competitor-analysis") {
        setupCompetitorAnalysisListeners();
    }

    function setupPredictionListeners(prefix) {
        const sectorEl = document.getElementById(`${prefix}-sector`);
        const companyEl = document.getElementById(`${prefix}-company`);
        const btnEl = document.getElementById(`btn-predict-${prefix}`);
        
        if (!sectorEl || !companyEl || !btnEl) return;
        
        // Sector Change
        sectorEl.addEventListener("change", () => {
            const sector = sectorEl.value;
            companyEl.innerHTML = '<option value="">Firma Seçin...</option>';
            companyEl.disabled = true;
            btnEl.disabled = true;
            
            resetPredictionResults(prefix);
            hideClassifierChart(prefix);
            
            if (sector) {
                let taskParam = prefix === "kz" ? "classification_kz" : (prefix === "dir" ? "classification_yon" : "");
                let url = `/api/companies?sector=${encodeURIComponent(sector)}&currency=${encodeURIComponent(currentCurrency)}`;
                if (taskParam) url += `&task=${taskParam}`;

                // Show loading state
                companyEl.innerHTML = '<option value="">⏳ Firmalar ve başarı oranları hesaplanıyor...</option>';
                companyEl.disabled = true;
                btnEl.disabled = true;
                btnEl.dataset._origText = btnEl.textContent;
                btnEl.textContent = "⏳ Veri Çekiliyor...";
                
                fetch(url)
                    .then(res => res.json())
                    .then(data => {
                        companyEl.innerHTML = '<option value="">Firma Seçin...</option>';
                        companyEl.disabled = false;
                        btnEl.textContent = btnEl.dataset._origText || btnEl.textContent;
                        // Keep btnEl.disabled=true until company is picked (handled by company change listener)
                        data.companies.forEach(comp => {
                            const opt = document.createElement("option");
                            if (typeof comp === "object") {
                                opt.value = comp.name;
                                opt.textContent = comp.label;
                            } else {
                                opt.value = comp;
                                opt.textContent = comp;
                            }
                            companyEl.appendChild(opt);
                        });
                    })
                    .catch(err => {
                        companyEl.innerHTML = '<option value="">⚠️ Yükleme Hatası!</option>';
                        companyEl.disabled = false;
                        btnEl.textContent = btnEl.dataset._origText || btnEl.textContent;
                        console.error(`[${prefix}] Şirket yüklenemedi:`, err);
                    });
            }
        });

        // Company Change
        companyEl.addEventListener("change", () => {
            const company = companyEl.value;
            btnEl.disabled = !company;
            
            resetPredictionResults(prefix);
            hideClassifierChart(prefix);
        });
    }

    function setupCompetitorAnalysisListeners() {
        const sectorEl = document.getElementById("comp-sector");
        const companyEl = document.getElementById("comp-company");
        const competitorEl = document.getElementById("comp-competitor");
        const btnEl = document.getElementById("btn-run-comp-analysis");
        const resultsCard = document.getElementById("comp-results-card");
        
        if (!sectorEl || !companyEl || !competitorEl || !btnEl || !resultsCard) return;
        
        let compChart = null;
        let responseData = null;
        let currentChartMode = "value"; // "value" or "rank"

        // Sector Change
        sectorEl.addEventListener("change", () => {
            const sector = sectorEl.value;
            companyEl.innerHTML = '<option value="">Firma Seçin...</option>';
            companyEl.disabled = true;
            competitorEl.innerHTML = '<option value="">Rakip Seçin (İsteğe Bağlı)...</option>';
            competitorEl.disabled = true;
            btnEl.disabled = true;
            resultsCard.style.display = "none";
            const chartCard = document.getElementById("comp-chart-card");
            if (chartCard) chartCard.style.display = "none";
            const tableCard = document.getElementById("comp-table-card");
            if (tableCard) tableCard.style.display = "none";
            document.getElementById("competitor-meta-section").style.display = "none";
            
            if (sector) {
                fetch(`/api/companies?sector=${encodeURIComponent(sector)}&task=ranking`)
                    .then(res => res.json())
                    .then(data => {
                        companyEl.disabled = false;
                        competitorEl.disabled = false;
                        
                        data.companies.forEach(comp => {
                            const opt1 = document.createElement("option");
                            const opt2 = document.createElement("option");
                            if (typeof comp === "object") {
                                opt1.value = comp.name;
                                opt1.textContent = comp.label;
                                opt2.value = comp.name;
                                opt2.textContent = comp.label;
                            } else {
                                opt1.value = comp;
                                opt1.textContent = comp;
                                opt2.value = comp;
                                opt2.textContent = comp;
                            }
                            companyEl.appendChild(opt1);
                            competitorEl.appendChild(opt2);
                        });
                    })
                    .catch(err => console.error(`[Competitor] Şirket yüklenemedi:`, err));
            }
        });

        // Company Change
        companyEl.addEventListener("change", () => {
            const selectedCompany = companyEl.value;
            btnEl.disabled = !selectedCompany;
            resultsCard.style.display = "none";
            const chartCard = document.getElementById("comp-chart-card");
            if (chartCard) chartCard.style.display = "none";
            const tableCard = document.getElementById("comp-table-card");
            if (tableCard) tableCard.style.display = "none";
            document.getElementById("competitor-meta-section").style.display = "none";
            
            // Filter out the selected main company from competitor options
            Array.from(competitorEl.options).forEach(opt => {
                if (opt.value !== "" && opt.value === selectedCompany) {
                    opt.disabled = true;
                    opt.style.display = "none";
                } else {
                    opt.disabled = false;
                    opt.style.display = "";
                }
            });
            
            if (competitorEl.value === selectedCompany) {
                competitorEl.value = "";
            }
        });

        // Competitor Change
        competitorEl.addEventListener("change", () => {
            resultsCard.style.display = "none";
            const chartCard = document.getElementById("comp-chart-card");
            if (chartCard) chartCard.style.display = "none";
            const tableCard = document.getElementById("comp-table-card");
            if (tableCard) tableCard.style.display = "none";
            document.getElementById("competitor-meta-section").style.display = "none";
        });

        // Run Competitor Analysis button click
        btnEl.addEventListener("click", () => {
            const sector = sectorEl.value;
            const company = companyEl.value;
            const competitor = competitorEl.value;
            
            btnEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> HESAPLANIYOR...';
            btnEl.disabled = true;

            fetch(`/api/competitor_analysis?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&competitor=${encodeURIComponent(competitor)}&currency=${currentCurrency}`)
                .then(res => res.json())
                .then(data => {
                    btnEl.innerHTML = '<i class="fa-solid fa-magnifying-glass-chart"></i> RAKİP ANALİZİ YAP';
                    btnEl.disabled = false;

                    if (data.error) {
                        alert(`Hata: ${data.error}`);
                        return;
                    }

                    responseData = data;
                    currentChartMode = "value"; // Reset to Net Profit view

                    // Populate company scorecard values
                    document.getElementById("comp-company-header").innerHTML = `<i class="fa-solid fa-industry"></i> ${data.company} Özet Performansı`;
                    document.getElementById("comp-avg-rank-text").textContent = `#${Math.round(data.avg_rank)}`;
                    document.getElementById("comp-best-rank-text").textContent = `#${data.best_rank} (${data.best_rank_period}. Çeyrek)`;
                    document.getElementById("comp-worst-rank-text").textContent = `#${data.worst_rank} (${data.worst_rank_period}. Çeyrek)`;

                    // Populate company extra stats
                    let companyStats = data.company_stats;
                    if (!companyStats && data.periods_data) {
                        const validPeriods = data.periods_data.filter(p => p.company_value !== null && p.company_value !== undefined);
                        companyStats = {
                            total_periods: validPeriods.length,
                            positive_periods: validPeriods.filter(p => p.company_value > 0).length,
                            negative_periods: validPeriods.filter(p => p.company_value <= 0).length,
                            above_avg_periods: validPeriods.filter(p => p.company_value > p.sector_avg).length,
                            above_median_periods: validPeriods.filter(p => p.company_value > p.sector_median).length
                        };
                    }

                    if (companyStats) {
                        const cs = companyStats;
                        document.getElementById("company-profit-loss-ratio").innerHTML = 
                            `<span style="color:var(--color-green)">+${cs.positive_periods}</span> / <span style="color:var(--accent-red)">-${cs.negative_periods}</span>`;
                        document.getElementById("company-above-avg-ratio").textContent = 
                            `${cs.above_avg_periods} / ${cs.total_periods} Çeyrek`;
                        document.getElementById("company-above-median-ratio").textContent = 
                            `${cs.above_median_periods} / ${cs.total_periods} Çeyrek`;

                        if (cs.total_periods > 0) {
                            const score = ((cs.positive_periods * 0.6) + (cs.above_median_periods * 0.4)) / cs.total_periods * 100;
                            updateRightPanelAIScore(score);
                        }
                    }

                    // Populate competitor scorecard if selected
                    const competitorMetaSec = document.getElementById("competitor-meta-section");
                    if (data.competitor && data.competitor_avg_rank != null) {
                        competitorMetaSec.style.display = "block";
                        document.getElementById("comp-competitor-header").innerHTML = `<i class="fa-solid fa-shield-halved"></i> ${data.competitor} Özet Performansı`;
                        document.getElementById("comp-competitor-avg-rank-text").textContent = `#${Math.round(data.competitor_avg_rank)}`;
                        document.getElementById("comp-competitor-best-rank-text").textContent = `#${data.competitor_best_rank} (${data.competitor_best_rank_period}. Çeyrek)`;
                        document.getElementById("comp-competitor-worst-rank-text").textContent = `#${data.competitor_worst_rank} (${data.competitor_worst_rank_period}. Çeyrek)`;
                        
                        let competitorStats = data.competitor_stats;
                        if (!competitorStats && data.periods_data) {
                            const validPeriods = data.periods_data.filter(p => p.competitor_value !== null && p.competitor_value !== undefined);
                            competitorStats = {
                                total_periods: validPeriods.length,
                                positive_periods: validPeriods.filter(p => p.competitor_value > 0).length,
                                negative_periods: validPeriods.filter(p => p.competitor_value <= 0).length,
                                above_avg_periods: validPeriods.filter(p => p.competitor_value > p.sector_avg).length,
                                above_median_periods: validPeriods.filter(p => p.competitor_value > p.sector_median).length
                            };
                        }

                        if (competitorStats) {
                            const cpts = competitorStats;
                            document.getElementById("competitor-profit-loss-ratio").innerHTML = 
                                `<span style="color:var(--color-green)">+${cpts.positive_periods}</span> / <span style="color:var(--accent-red)">-${cpts.negative_periods}</span>`;
                            document.getElementById("competitor-above-avg-ratio").textContent = 
                                `${cpts.above_avg_periods} / ${cpts.total_periods} Çeyrek`;
                            document.getElementById("competitor-above-median-ratio").textContent = 
                                `${cpts.above_median_periods} / ${cpts.total_periods} Çeyrek`;
                        }
                    } else {
                        competitorMetaSec.style.display = "none";
                    }

                    // Narrative Turkish text
                    document.getElementById("comp-narrative-text").innerHTML = data.narrative;

                    // Populate Breakdown Table
                    const thead = document.querySelector("#comp-period-table thead");
                    const tbody = document.querySelector("#comp-period-table tbody");
                    
                    const formatVal = (val) => {
                        if (val == null || isNaN(val)) return "-";
                        return Math.round(val).toLocaleString('tr-TR') + " " + currentCurrency;
                    };

                    if (data.competitor) {
                        thead.innerHTML = `
                            <tr>
                                <th style="min-width: 110px;">Dönem</th>
                                <th style="min-width: 140px;">${data.company} Kârı</th>
                                <th style="min-width: 110px;">${data.company} Sırası</th>
                                <th style="min-width: 140px;">${data.competitor} Kârı</th>
                                <th style="min-width: 110px;">${data.competitor} Sırası</th>
                                <th style="min-width: 150px;">Sektör Ort. / Medyanı</th>
                                <th style="min-width: 180px;">Sektörel Konumlar</th>
                            </tr>
                        `;
                        
                        tbody.innerHTML = "";
                        data.periods_data.forEach(p => {
                            const tr = document.createElement("tr");
                            let coBadgeColor = p.percentile >= 75 ? "var(--color-green)" : p.percentile >= 50 ? "var(--color-blue)" : p.percentile >= 25 ? "var(--color-gold)" : "var(--accent-red)";
                            let compBadgeColor = p.competitor_percentile >= 75 ? "var(--color-green)" : p.competitor_percentile >= 50 ? "var(--color-blue)" : p.competitor_percentile >= 25 ? "var(--color-gold)" : "var(--accent-red)";
                            
                            tr.innerHTML = `
                                <td><strong>${p.period}. Çeyrek</strong></td>
                                <td style="color: #ffb300; font-weight: bold;">${formatVal(p.company_value)}</td>
                                <td><strong>#${p.company_rank}</strong> / ${p.total_companies}</td>
                                <td style="color: #a855f7; font-weight: bold;">${formatVal(p.competitor_value)}</td>
                                <td><strong>#${p.competitor_rank}</strong> / ${p.total_companies}</td>
                                <td style="font-size: 11.5px; color: #94a3b8;">
                                    Ort: ${formatVal(p.sector_avg)}<br>Med: ${formatVal(p.sector_median)}
                                </td>
                                <td style="font-size: 11px; line-height: 1.4;">
                                    <span style="color: ${coBadgeColor}; font-weight: 500;">${data.company}: ${p.position_desc}</span><br>
                                    <span style="color: ${compBadgeColor}; font-weight: 500;">${data.competitor}: ${p.competitor_position_desc}</span>
                                </td>
                            `;
                            tbody.appendChild(tr);
                        });
                    } else {
                        thead.innerHTML = `
                            <tr>
                                <th style="min-width: 120px;">Dönem</th>
                                <th style="min-width: 160px;">Firma Değeri</th>
                                <th style="min-width: 160px;">Sektör Ortalaması</th>
                                <th style="min-width: 160px;">Sektör Medyanı</th>
                                <th style="min-width: 150px;">Sıralama / Firma</th>
                                <th style="min-width: 130px;">Yüzdelik Dilim</th>
                                <th style="min-width: 180px;">Sektör Konumu</th>
                            </tr>
                        `;
                        
                        tbody.innerHTML = "";
                        data.periods_data.forEach(p => {
                            const tr = document.createElement("tr");
                            let badgeColor = p.percentile >= 75 ? "var(--color-green)" : p.percentile >= 50 ? "var(--color-blue)" : p.percentile >= 25 ? "var(--color-gold)" : "var(--accent-red)";
                            
                            tr.innerHTML = `
                                <td><strong>${p.period}. Çeyrek</strong></td>
                                <td style="color: #ffb300; font-weight: bold;">${formatVal(p.company_value)}</td>
                                <td>${formatVal(p.sector_avg)}</td>
                                <td>${formatVal(p.sector_median)}</td>
                                <td><strong>#${p.company_rank}</strong> / ${p.total_companies}</td>
                                <td>%${p.percentile.toFixed(1)}</td>
                                <td style="color: ${badgeColor}; font-size: 12px; font-weight: 500;">${p.position_desc}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                    }

                    resultsCard.style.display = "block";
                    const chartCard = document.getElementById("comp-chart-card");
                    if (chartCard) chartCard.style.display = "block";
                    const tableCard = document.getElementById("comp-table-card");
                    if (tableCard) tableCard.style.display = "block";

                    // Chart Renderer Helper
                    function renderChart() {
                        const ctx = document.getElementById("comp-rank-chart").getContext("2d");
                        if (compChart) {
                            compChart.destroy();
                        }

                        const labels = responseData.periods_data.map(p => `${p.period}. Çeyrek`);
                        let datasets = [];

                        if (currentChartMode === "value") {
                            // Selected Company
                            datasets.push({
                                label: `${responseData.company} Gerçekleşen Kâr`,
                                data: responseData.periods_data.map(p => p.company_value),
                                borderColor: '#ffb300',
                                backgroundColor: 'rgba(255, 179, 0, 0.05)',
                                borderWidth: 3,
                                pointRadius: 4,
                                tension: 0.2,
                                fill: false
                            });
                            datasets.push({
                                label: `${responseData.company} Gelecek Çeyrek Tahmini`,
                                data: responseData.periods_data.map(p => p.company_pred_value),
                                borderColor: 'rgba(255, 179, 0, 0.6)',
                                backgroundColor: 'transparent',
                                borderWidth: 2,
                                borderDash: [6, 4],
                                pointRadius: 3,
                                tension: 0.2,
                                fill: false
                            });

                            // Competitor (optional)
                            if (responseData.competitor) {
                                datasets.push({
                                    label: `${responseData.competitor} Gerçekleşen Kâr`,
                                    data: responseData.periods_data.map(p => p.competitor_value),
                                    borderColor: '#a855f7',
                                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    tension: 0.2,
                                    fill: false
                                });
                                datasets.push({
                                    label: `${responseData.competitor} Gelecek Çeyrek Tahmini`,
                                    data: responseData.periods_data.map(p => p.competitor_pred_value),
                                    borderColor: 'rgba(168, 85, 247, 0.6)',
                                    backgroundColor: 'transparent',
                                    borderWidth: 2,
                                    borderDash: [6, 4],
                                    pointRadius: 3,
                                    tension: 0.2,
                                    fill: false
                                });
                            }

                            // Sector Metrics
                            datasets.push({
                                label: "Sektör Ortalaması",
                                data: responseData.periods_data.map(p => p.sector_avg),
                                borderColor: '#00d2ff',
                                backgroundColor: 'transparent',
                                borderWidth: 1.5,
                                borderDash: [4, 4],
                                pointRadius: 0,
                                tension: 0.2,
                                fill: false
                            });
                            datasets.push({
                                label: "Sektör Medyanı",
                                data: responseData.periods_data.map(p => p.sector_median),
                                borderColor: '#00f27c',
                                backgroundColor: 'transparent',
                                borderWidth: 1.5,
                                borderDash: [2, 2],
                                pointRadius: 0,
                                tension: 0.2,
                                fill: false
                            });
                        } else {
                            // Rank View
                            datasets.push({
                                label: `${responseData.company} Sektörel Sıra`,
                                data: responseData.periods_data.map(p => p.company_rank),
                                borderColor: '#ffb300',
                                backgroundColor: 'rgba(255, 179, 0, 0.1)',
                                borderWidth: 3,
                                pointRadius: 5,
                                tension: 0.2,
                                fill: false
                            });

                            if (responseData.competitor) {
                                datasets.push({
                                    label: `${responseData.competitor} Sektörel Sıra`,
                                    data: responseData.periods_data.map(p => p.competitor_rank),
                                    borderColor: '#a855f7',
                                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                                    borderWidth: 3,
                                    pointRadius: 5,
                                    tension: 0.2,
                                    fill: false
                                });
                            }
                        }

                        let yScaleConfig = {
                            grid: { color: "rgba(255, 255, 255, 0.04)" },
                            ticks: {
                                color: "#94a3b8",
                                font: { family: 'Outfit', size: 11 }
                            }
                        };

                        if (currentChartMode === "value") {
                            yScaleConfig.ticks.callback = function(value) {
                                if (Math.abs(value) >= 1e6) {
                                    return (value / 1e6).toFixed(1) + "M";
                                } else if (Math.abs(value) >= 1e3) {
                                    return (value / 1e3).toFixed(0) + "K";
                                }
                                return value;
                            };
                        } else {
                            yScaleConfig.reverse = true;
                            yScaleConfig.min = 1;
                            yScaleConfig.ticks.stepSize = 1;
                            yScaleConfig.ticks.callback = function(value) {
                                return "#" + value;
                            };
                        }

                        compChart = new Chart(ctx, {
                            type: "line",
                            data: {
                                labels: labels,
                                datasets: datasets
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                onClick: (e, elements) => {
                                    if (elements.length > 0) {
                                        const firstPoint = elements[0];
                                        const periodIndex = firstPoint.index;
                                        const periodData = responseData.periods_data[periodIndex];
                                        if (periodData) {
                                            showPeriodDetailsModal(periodData);
                                        }
                                    }
                                },
                                plugins: {
                                    legend: {
                                        labels: {
                                            color: '#94a3b8',
                                            font: { family: 'Outfit', size: 12 }
                                        }
                                    },
                                    tooltip: {
                                        backgroundColor: '#0f1524',
                                        titleFont: { family: 'Outfit', size: 13, weight: 'bold' },
                                        bodyFont: { family: 'Outfit', size: 12 },
                                        borderWidth: 1,
                                        borderColor: 'rgba(255,255,255,0.06)',
                                        callbacks: {
                                            label: function(context) {
                                                let val = context.raw;
                                                if (currentChartMode === "value") {
                                                    return `${context.dataset.label}: ${Math.round(val).toLocaleString('tr-TR')} ${currentCurrency}`;
                                                } else {
                                                    return `${context.dataset.label}: #${val}. Sıra`;
                                                }
                                            }
                                        }
                                    },
                                    zoom: {
                                        pan: {
                                            enabled: true,
                                            mode: 'x',
                                            threshold: 10
                                        },
                                        zoom: {
                                            wheel: {
                                                enabled: true
                                            },
                                            pinch: {
                                                enabled: true
                                            },
                                            mode: 'x'
                                        }
                                    }
                                },
                                scales: {
                                    y: yScaleConfig,
                                    x: {
                                        grid: { display: false },
                                        ticks: {
                                            color: "#94a3b8",
                                            font: { family: 'Outfit', size: 11 }
                                        }
                                    }
                                }
                            }
                        });

                        function showPeriodDetailsModal(p) {
                            const modal = document.getElementById("period-detail-modal");
                            if (!modal) return;

                            document.getElementById("modal-period-title").textContent = `${p.period}. Çeyrek Sektörel Detayları`;
                            
                            // Ana Firma
                            document.getElementById("modal-company-name").innerHTML = `<i class="fa-solid fa-industry"></i> ${responseData.company}`;
                            document.getElementById("modal-company-value").textContent = formatVal(p.company_value);
                            document.getElementById("modal-company-pred").textContent = formatVal(p.company_pred_value);
                            document.getElementById("modal-company-rank").textContent = `#${p.company_rank} / ${p.total_companies}`;
                            document.getElementById("modal-company-pos").textContent = p.position_desc;

                            // Rakip Firma
                            const competitorSec = document.getElementById("modal-competitor-section");
                            if (responseData.competitor && p.competitor_value !== null) {
                                competitorSec.style.display = "block";
                                document.getElementById("modal-competitor-name").innerHTML = `<i class="fa-solid fa-shield-halved"></i> ${responseData.competitor}`;
                                document.getElementById("modal-competitor-value").textContent = formatVal(p.competitor_value);
                                document.getElementById("modal-competitor-pred").textContent = formatVal(p.competitor_pred_value);
                                document.getElementById("modal-competitor-rank").textContent = `#${p.competitor_rank} / ${p.total_companies}`;
                                document.getElementById("modal-competitor-pos").textContent = p.competitor_position_desc;
                            } else {
                                competitorSec.style.display = "none";
                            }

                            // Sektör
                            document.getElementById("modal-sector-avg").textContent = formatVal(p.sector_avg);
                            document.getElementById("modal-sector-median").textContent = formatVal(p.sector_median);
                            document.getElementById("modal-sector-max").textContent = formatVal(p.sector_max);
                            document.getElementById("modal-sector-min").textContent = formatVal(p.sector_min);

                            // Show modal
                            modal.style.display = "flex";
                        }

                        // Modal close event handlers
                        const modalEl = document.getElementById("period-detail-modal");
                        const closeModalX = document.getElementById("close-period-modal");
                        const closeModalBtn = document.getElementById("close-period-modal-btn");
                        
                        if (closeModalX) {
                            closeModalX.onclick = () => { modalEl.style.display = "none"; };
                        }
                        if (closeModalBtn) {
                            closeModalBtn.onclick = () => { modalEl.style.display = "none"; };
                        }
                        
                        // Close on outside window click
                        window.addEventListener("click", (e) => {
                            if (e.target === modalEl) {
                                modalEl.style.display = "none";
                            }
                        });

                    // Reset zoom button wire up
                    const resetZoomBtn = document.getElementById("btn-reset-zoom");
                    if (resetZoomBtn) {
                        resetZoomBtn.onclick = () => {
                            if (compChart) {
                                compChart.resetZoom();
                            }
                        };
                    }
                    }

                    // Setup Chart Mode Toggles
                    const btnValue = document.getElementById("btn-chart-mode-value");
                    const btnRank = document.getElementById("btn-chart-mode-rank");
                    
                    if (btnValue && btnRank) {
                        btnValue.onclick = () => {
                            if (currentChartMode === "value") return;
                            currentChartMode = "value";
                            btnValue.style.background = "var(--color-blue)";
                            btnValue.style.color = "#fff";
                            btnRank.style.background = "transparent";
                            btnRank.style.color = "#94a3b8";
                            renderChart();
                        };
                        btnRank.onclick = () => {
                            if (currentChartMode === "rank") return;
                            currentChartMode = "rank";
                            btnRank.style.background = "var(--color-blue)";
                            btnRank.style.color = "#fff";
                            btnValue.style.background = "transparent";
                            btnValue.style.color = "#94a3b8";
                            renderChart();
                        };
                        
                        // Default Style
                        btnValue.style.background = "var(--color-blue)";
                        btnValue.style.color = "#fff";
                        btnRank.style.background = "transparent";
                        btnRank.style.color = "#94a3b8";
                    }

                    renderChart();
                })
                .catch(err => {
                    btnEl.innerHTML = '<i class="fa-solid fa-magnifying-glass-chart"></i> RAKİP ANALİZİ YAP';
                    btnEl.disabled = false;
                    console.error("Competitor analysis request failed:", err);
                    alert(`Hata: ${err.message}`);
                });
        });
    }

    // Load Company Features for a Specific Tab (What-if layout)
    function loadCompanyFeatures(prefix) {
        const sectorEl = document.getElementById(`${prefix}-sector`);
        const companyEl = document.getElementById(`${prefix}-company`);
        const periodEl = document.getElementById(`${prefix}-period`);
        const container = document.getElementById(`${prefix}-features-container`);
        const labelEl = document.getElementById(`${prefix}-current-profit-label`);
        const btnEl = document.getElementById(`btn-predict-${prefix}`);
        
        if (!sectorEl || !companyEl || !periodEl || !container || !labelEl || !btnEl) return;
        
        const sector = sectorEl.value;
        const company = companyEl.value;
        const period = periodEl.value;
        
        container.innerHTML = '<div class="empty-state-small"><i class="fa-solid fa-circle-notch fa-spin"></i> Finansal kalemler çekiliyor...</div>';
        
        // V2 matches the Stacking / Scaled layout
        fetch(`/api/company_features?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&period=${period}&currency=${currentCurrency}&version=V2`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    container.innerHTML = `<div class="empty-state-small text-red">${data.error}</div>`;
                    btnEl.disabled = true;
                    return;
                }
                
                container.innerHTML = "";
                labelEl.textContent = `Cari Kâr: ${Math.round(data.current_profit).toLocaleString('tr-TR')} ${currentCurrency}`;
                labelEl.dataset.currentProfit = data.current_profit;

                // Enable and set seasonality and anomaly
                const mevsimEl = document.getElementById(`${prefix}-mevsim`);
                const anomaliEl = document.getElementById(`${prefix}-anomali`);
                if (mevsimEl) {
                    mevsimEl.disabled = false;
                    mevsimEl.value = data.current_mevsim;
                }
                if (anomaliEl) {
                    anomaliEl.disabled = false;
                    anomaliEl.value = data.current_anomali;
                }

                // Sort features alphabetically and append numeric input forms
                const sortedKeys = Object.keys(data.features).sort();
                sortedKeys.forEach(key => {
                    const val = data.features[key];
                    const div = document.createElement("div");
                    div.className = "feature-item";
                    
                    const label = document.createElement("label");
                    label.textContent = key;
                    label.title = key;
                    
                    const input = document.createElement("input");
                    input.type = "number";
                    input.step = "any";
                    input.value = val;
                    input.dataset.featureName = key;
                    
                    div.appendChild(label);
                    div.appendChild(input);
                    container.appendChild(div);
                });
                
                btnEl.disabled = false;
            })
            .catch(err => {
                container.innerHTML = `<div class="empty-state-small text-red">Yüklenemedi: ${err.message}</div>`;
                btnEl.disabled = true;
            });
    }

    // Reset results labels to waiting state
    function resetPredictionResults(prefix) {
        const resultsCard = document.getElementById(`${prefix}-results-card`);
        if (resultsCard) {
            resultsCard.style.display = "none";
        }
        const tableCard = document.getElementById(`${prefix}-table-card`);
        if (tableCard) {
            tableCard.style.display = "none";
        }
        const tbody = document.querySelector(`#${prefix}-period-table tbody`);
        if (tbody) {
            tbody.innerHTML = "";
        }
    }

    // Run AI prediction when buttons are clicked
    // ── K/Z CLASSIFICATION PREDICTION BUTTON ──────────────────────────────────
    const btnPredictKz = document.getElementById("btn-predict-kz");
    if (btnPredictKz) {
        btnPredictKz.addEventListener("click", () => {
            runPredict("kz");
        });
    }
    // ── DIRECTION CLASSIFICATION PREDICTION BUTTON ────────────────────────────
    const btnPredictDir = document.getElementById("btn-predict-dir");
    if (btnPredictDir) {
        btnPredictDir.addEventListener("click", () => {
            runPredict("dir");
        });
    }

    function runPredict(prefix) {
        const btn = document.getElementById(`btn-predict-${prefix}`);
        if (!btn) return;
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> HESAPLANIYOR...';

        const sector = document.getElementById(`${prefix}-sector`).value;
        const company = document.getElementById(`${prefix}-company`).value;

        fetch(`/api/predict_all?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&currency=${currentCurrency}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(`Analiz hatası: ${data.error}`);
                return;
            }

            // Cache prediction results on the canvas element for the chart
            const canvasEl = document.getElementById(`${prefix}-trend-line-chart`);
            if (canvasEl) {
                canvasEl.dataset.results = JSON.stringify(data.results);
                canvasEl.dataset.highlightErrors = "false";
            }

            // Show/Reset the error toggle button
            const errToggleBtn = document.getElementById(`${prefix}-toggle-errors-btn`);
            if (errToggleBtn) {
                errToggleBtn.style.display = "inline-flex";
                errToggleBtn.classList.remove("active");
                errToggleBtn.style.background = "rgba(239, 68, 68, 0.1)";
                errToggleBtn.style.color = "#ef4444";
                errToggleBtn.style.boxShadow = "none";
            }

            // Show results card
            const resultsCard = document.getElementById(`${prefix}-results-card`);
            if (resultsCard) {
                resultsCard.style.display = "block";
            }

            // Show table card
            const tableCard = document.getElementById(`${prefix}-table-card`);
            if (tableCard) {
                tableCard.style.display = "block";
            }

            // Update stats
            if (prefix === "kz") {
                document.getElementById("kz-total-periods-text").textContent = data.total_kz_count;
                document.getElementById("kz-correct-preds-text").textContent = data.correct_kz_count;
                document.getElementById("kz-accuracy-text").textContent = data.accuracy_kz !== null ? `%${data.accuracy_kz.toFixed(1)}` : "-";
                document.getElementById("badge-kz-ver").textContent = `${data.cls_kz_ver} Modeli | ${data.cls_kz_alg}`;
                document.getElementById("kz-narrative-text").innerHTML = data.report_kz;
                if (data.accuracy_kz !== null && data.accuracy_kz !== undefined) {
                    updateRightPanelAIScore(data.accuracy_kz);
                }
            } else {
                document.getElementById("dir-total-periods-text").textContent = data.total_yon_count;
                document.getElementById("dir-correct-preds-text").textContent = data.correct_yon_count;
                document.getElementById("dir-accuracy-text").textContent = data.accuracy_yon !== null ? `%${data.accuracy_yon.toFixed(1)}` : "-";
                document.getElementById("badge-dir-ver").textContent = `${data.cls_yon_ver} Modeli | ${data.cls_yon_alg}`;
                document.getElementById("dir-narrative-text").innerHTML = data.report_yon;
                if (data.accuracy_yon !== null && data.accuracy_yon !== undefined) {
                    updateRightPanelAIScore(data.accuracy_yon);
                }
            }

            // Populate table
            const tbody = document.querySelector(`#${prefix}-period-table tbody`);
            if (tbody) {
                tbody.innerHTML = "";

                let correctCount = 0;
                let evaluatedCount = 0;

                data.results.forEach(r => {
                    const tr = document.createElement("tr");

                    // 1. Period
                    const tdPeriod = document.createElement("td");
                    tdPeriod.innerHTML = `<strong>${r.period}. Çeyrek</strong>`;
                    tr.appendChild(tdPeriod);

                    if (prefix === "dir") {
                        // 2. Kâr Yönü Tahmini
                        const tdPred = document.createElement("td");
                        const predLabel = r.pred_yon === 1 ? "Kâr Artışı" : "Kâr Azalışı";
                        const predBadge = r.pred_yon === 1 ? "badge-success" : "badge-danger";
                        tdPred.innerHTML = `<span class="badge ${predBadge}">${predLabel}</span>`;
                        tr.appendChild(tdPred);

                        // 3. Gerçekleşen Yön
                        const tdAct = document.createElement("td");
                        if (r.actual_yon === null || r.actual_yon === undefined) {
                            tdAct.textContent = "-";
                        } else {
                            const actLabel = r.actual_yon === 1 ? "Kâr Artışı" : "Kâr Azalışı";
                            const actBadge = r.actual_yon === 1 ? "badge-success" : "badge-danger";
                            tdAct.innerHTML = `<span class="badge ${actBadge}">${actLabel}</span>`;
                        }
                        tr.appendChild(tdAct);

                        // 4. Yön Tahmin Sonucu
                        const tdRes = document.createElement("td");
                        if (r.actual_yon === null || r.actual_yon === undefined) {
                            tdRes.textContent = "-";
                        } else {
                            const isCorrect = r.pred_yon === r.actual_yon;
                            if (isCorrect) correctCount++;
                            evaluatedCount++;
                            tdRes.innerHTML = isCorrect ? 
                                '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Başarılı</span>' :
                                '<span class="badge badge-danger"><i class="fa-solid fa-circle-xmark"></i> Başarısız</span>';
                        }
                        tr.appendChild(tdRes);

                        // 5. Kümülatif Başarı
                        const tdCum = document.createElement("td");
                        if (r.actual_yon === null || r.actual_yon === undefined || evaluatedCount === 0) {
                            tdCum.textContent = "-";
                        } else {
                            const cumAcc = (correctCount / evaluatedCount) * 100;
                            tdCum.innerHTML = `<span style="color: var(--color-gold); font-weight: bold;"><i class="fa-solid fa-chart-line"></i> %${cumAcc.toFixed(1)}</span> <span style="font-size: 11px; color: #94a3b8;">(${correctCount}/${evaluatedCount})</span>`;
                        }
                        tr.appendChild(tdCum);

                        // 6. Kâr Başarımı (Sektör Kıyaslama) - Cross Model View
                        const tdKzCompare = document.createElement("td");
                        const predKzLabel = r.pred_kz === 1 ? "Sektör Üstü" : "Sektör Altı";
                        const predKzBadge = r.pred_kz === 1 ? "badge-success" : "badge-danger";
                        if (r.actual_kz === null || r.actual_kz === undefined) {
                            tdKzCompare.innerHTML = `<span class="badge ${predKzBadge}">${predKzLabel} (T)</span>`;
                        } else {
                            const actKzLabel = r.actual_kz === 1 ? "Sektör Üstü" : "Sektör Altı";
                            const actKzBadge = r.actual_kz === 1 ? "badge-success" : "badge-danger";
                            tdKzCompare.innerHTML = `<span class="badge ${predKzBadge}">${predKzLabel} (T)</span> <i class="fa-solid fa-arrow-right-long" style="font-size: 10px; color: #94a3b8; margin: 0 4px;"></i> <span class="badge ${actKzBadge}">${actKzLabel} (G)</span>`;
                        }
                        tr.appendChild(tdKzCompare);

                    } else { // prefix === "kz"
                        // 2. Kâr Başarımı Tahmini
                        const tdPred = document.createElement("td");
                        const predLabel = r.pred_kz === 1 ? "Sektör Üstü Kâr" : "Sektör Altı Kâr";
                        const predBadge = r.pred_kz === 1 ? "badge-success" : "badge-danger";
                        tdPred.innerHTML = `<span class="badge ${predBadge}">${predLabel}</span>`;
                        tr.appendChild(tdPred);

                        // 3. Gerçekleşen Başarım
                        const tdAct = document.createElement("td");
                        if (r.actual_kz === null || r.actual_kz === undefined) {
                            tdAct.textContent = "-";
                        } else {
                            const actLabel = r.actual_kz === 1 ? "Sektör Üstü" : "Sektör Altı";
                            const actBadge = r.actual_kz === 1 ? "badge-success" : "badge-danger";
                            tdAct.innerHTML = `<span class="badge ${actBadge}">${actLabel}</span>`;
                        }
                        tr.appendChild(tdAct);

                        // 4. Tahmin Sonucu
                        const tdRes = document.createElement("td");
                        if (r.actual_kz === null || r.actual_kz === undefined) {
                            tdRes.textContent = "-";
                        } else {
                            const isCorrect = r.pred_kz === r.actual_kz;
                            if (isCorrect) correctCount++;
                            evaluatedCount++;
                            tdRes.innerHTML = isCorrect ? 
                                '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Başarılı</span>' :
                                '<span class="badge badge-danger"><i class="fa-solid fa-circle-xmark"></i> Başarısız</span>';
                        }
                        tr.appendChild(tdRes);

                        // 5. Kümülatif Başarı
                        const tdCum = document.createElement("td");
                        if (r.actual_kz === null || r.actual_kz === undefined || evaluatedCount === 0) {
                            tdCum.textContent = "-";
                        } else {
                            const cumAcc = (correctCount / evaluatedCount) * 100;
                            tdCum.innerHTML = `<span style="color: var(--color-gold); font-weight: bold;"><i class="fa-solid fa-chart-line"></i> %${cumAcc.toFixed(1)}</span> <span style="font-size: 11px; color: #94a3b8;">(${correctCount}/${evaluatedCount})</span>`;
                        }
                        tr.appendChild(tdCum);

                        // 6. Kâr Değişim Yönü (Trend Analizi) - Cross Model View
                        const tdYonCompare = document.createElement("td");
                        const predYonLabel = r.pred_yon === 1 ? "Artış" : "Azalış";
                        const predYonBadge = r.pred_yon === 1 ? "badge-success" : "badge-danger";
                        if (r.actual_yon === null || r.actual_yon === undefined) {
                            tdYonCompare.innerHTML = `<span class="badge ${predYonBadge}">${predYonLabel} (T)</span>`;
                        } else {
                            const actYonLabel = r.actual_yon === 1 ? "Artış" : "Azalış";
                            const actYonBadge = r.actual_yon === 1 ? "badge-success" : "badge-danger";
                            tdYonCompare.innerHTML = `<span class="badge ${predYonBadge}">${predYonLabel} (T)</span> <i class="fa-solid fa-arrow-right-long" style="font-size: 10px; color: #94a3b8; margin: 0 4px;"></i> <span class="badge ${actYonBadge}">${actYonLabel} (G)</span>`;
                        }
                        tr.appendChild(tdYonCompare);
                    }

                    // 7. Hibrit Karar Sinyali
                    const tdVerdict = document.createElement("td");
                    let verdict = "";
                    let verdictBadge = "";
                    let verdictIcon = "";

                    if (r.pred_kz === 1 && r.pred_yon === 1) {
                        verdict = "Güçlü Al (Sektör Üstü & Artış)";
                        verdictBadge = "badge-success";
                        verdictIcon = "fa-solid fa-circle-arrow-up";
                    } else if (r.pred_kz === 1 && r.pred_yon === 0) {
                        verdict = "Pozitif Tut (Sektör Üstü & Azalış)";
                        verdictBadge = "badge-info";
                        verdictIcon = "fa-solid fa-circle-right";
                    } else if (r.pred_kz === 0 && r.pred_yon === 1) {
                        verdict = "Temkinli Al (Sektör Altı & Artış)";
                        verdictBadge = "badge-warning";
                        verdictIcon = "fa-solid fa-circle-notch";
                    } else { // 0 & 0
                        verdict = "Güçlü Sat (Sektör Altı & Azalış)";
                        verdictBadge = "badge-danger";
                        verdictIcon = "fa-solid fa-circle-arrow-down";
                    }
                    tdVerdict.innerHTML = `<span class="badge ${verdictBadge}" style="display: inline-flex; align-items: center; gap: 5px;"><i class="${verdictIcon}"></i> ${verdict}</span>`;
                    tr.appendChild(tdVerdict);

                    // 8. Durum Koşulları (Seasonality & Anomaly)
                    const tdConditions = document.createElement("td");
                    const mevsimHTML = `<span style="color: var(--color-teal); margin-right: 8px;"><i class="fa-solid fa-cloud-sun"></i> M${r.mevsim}</span>`;
                    const anomaliHTML = r.anomali === 1 ?
                        '<span class="badge badge-danger" style="font-size: 10px; padding: 2px 4px;"><i class="fa-solid fa-triangle-exclamation"></i> Anomali</span>' :
                        '<span class="badge badge-success" style="font-size: 10px; padding: 2px 4px;"><i class="fa-solid fa-circle-check"></i> Normal</span>';
                    tdConditions.innerHTML = `${mevsimHTML} ${anomaliHTML}`;
                    tr.appendChild(tdConditions);

                    tbody.appendChild(tr);
                });
            }

            // Load interactive comparison chart
            loadClassifierTrendChart(prefix, sector, company);
        })
        .catch(err => {
            alert(`Analiz çalıştırılamadı: ${err.message}`);
        })
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
        });
    }

    // ── TAB 2: SECTORAL TREND ANALYSIS ────────────────────────────────────────
    const trendSector = document.getElementById("trend-sector");
    const trendCompany = document.getElementById("trend-company");
    const trendFeaturesList = document.getElementById("trend-features-list");
    const chartPlaceholder = document.getElementById("chart-placeholder");
    const canvasContainer = document.querySelector("#tab-trend .canvas-container");

    function getSelectedTrendCompanies() {
        const companyEl = document.getElementById("trend-company");
        if (!companyEl) return [];
        const selected = [];
        for (let option of companyEl.options) {
            if (option.selected) {
                selected.push(option.value);
            }
        }
        return selected;
    }

    // Toggle custom multi-select dropdown
    const msTrigger = document.getElementById("company-multiselect-trigger");
    const msDropdown = document.getElementById("company-multiselect-dropdown");
    const msPlaceholder = document.getElementById("company-multiselect-placeholder");
    const checkboxContainer = document.getElementById("company-checkboxes-container");
    const companySearchInput = document.getElementById("company-search");

    if (trendSector && trendCompany && msTrigger && msDropdown && msPlaceholder && checkboxContainer && companySearchInput) {
        msTrigger.addEventListener("click", (e) => {
            e.stopPropagation();
            const sector = trendSector.value;
            if (!sector) return; // Don't open if no sector is selected
            const isOpen = msDropdown.style.display === "block";
            msDropdown.style.display = isOpen ? "none" : "block";
            if (!isOpen) {
                companySearchInput.focus();
            }
        });

        document.addEventListener("click", (e) => {
            if (!e.target.closest(".custom-multiselect-group")) {
                msDropdown.style.display = "none";
            }
        });

        companySearchInput.addEventListener("input", function(e) {
            const query = e.target.value.toLowerCase();
            const labels = checkboxContainer.querySelectorAll(".feature-checkbox-label");
            labels.forEach(label => {
                const text = label.textContent.toLowerCase();
                if (text.includes(query)) {
                    label.style.display = "flex";
                } else {
                    label.style.display = "none";
                }
            });
        });

        function syncCheckboxesToHiddenSelect() {
            const checkedBoxes = Array.from(checkboxContainer.querySelectorAll("input[type='checkbox']:checked"));
            const selectedValues = checkedBoxes.map(cb => cb.value);
            
            Array.from(trendCompany.options).forEach(opt => {
                opt.selected = selectedValues.includes(opt.value);
            });
            
            if (selectedValues.length === 0) {
                msPlaceholder.textContent = "Firma Seçin...";
                msPlaceholder.style.color = "#94a3b8";
            } else {
                msPlaceholder.textContent = `${selectedValues.length} Firma Seçildi`;
                msPlaceholder.style.color = "#e2e8f0";
            }
            
            trendCompany.dispatchEvent(new Event("change"));
        }

        trendSector.addEventListener("change", () => {
            const sector = trendSector.value;
            trendCompany.innerHTML = '';
            checkboxContainer.innerHTML = '<div class="empty-state-small">Sektör seçildiğinde firmalar listelenecektir.</div>';
            msPlaceholder.textContent = "Firma Seçin...";
            msPlaceholder.style.color = "#94a3b8";
            companySearchInput.value = '';
            resetTrendChart();
            const listEl = document.getElementById("trend-features-list");
            if (listEl) {
                listEl.innerHTML = '<div class="empty-state-small">Firma seçildiğinde özellikler listelenecektir.</div>';
            }

            if (sector) {
                checkboxContainer.innerHTML = '<div class="empty-state-small"><i class="fa-solid fa-circle-notch fa-spin"></i> Firmalar yükleniyor...</div>';
                fetch(`/api/companies?sector=${encodeURIComponent(sector)}`)
                    .then(res => res.json())
                    .then(data => {
                        checkboxContainer.innerHTML = '';
                        trendCompany.innerHTML = '';
                        
                        data.companies.forEach(comp => {
                            const compName = typeof comp === "object" ? comp.name : comp;
                            const compLabel = typeof comp === "object" ? comp.label : comp;
                            
                            // Dummy hidden select options
                            const opt = document.createElement("option");
                            opt.value = compName;
                            opt.textContent = compName;
                            trendCompany.appendChild(opt);
                            
                            // Custom dropdown checkbox item
                            const label = document.createElement("label");
                            label.className = "feature-checkbox-label";
                            label.style.width = "100%";
                            label.style.display = "flex";
                            label.style.alignItems = "center";
                            label.style.gap = "10px";
                            label.style.cursor = "pointer";
                            
                            const cb = document.createElement("input");
                            cb.type = "checkbox";
                            cb.value = compName;
                            cb.className = "company-trend-checkbox";
                            cb.style.cursor = "pointer";
                            
                            const span = document.createElement("span");
                            span.textContent = compLabel;
                            
                            label.appendChild(cb);
                            label.appendChild(span);
                            checkboxContainer.appendChild(label);
                            
                            cb.addEventListener("change", () => {
                                syncCheckboxesToHiddenSelect();
                            });
                        });
                    })
                    .catch(err => console.error("Trend firmaları yükleme hatası:", err));
            }
        });

        trendCompany.addEventListener("change", () => {
            const selected = getSelectedTrendCompanies();
            const listEl = document.getElementById("trend-features-list");
            if (selected.length > 0) {
                // If features are already selected, just update the plot with the new company
                const alreadyChecked = listEl ? listEl.querySelectorAll("input[type='checkbox']:checked") : [];
                if (alreadyChecked.length > 0) {
                    updateTrendPlot();
                } else {
                    loadTrendFeatures();
                }
            } else {
                if (listEl) {
                    listEl.innerHTML = '<div class="empty-state-small">Firma seçildiğinde özellikler listelenecektir.</div>';
                }
                resetTrendChart();
            }
        });

        // Sector average toggle change listener
        const showAvgEl = document.getElementById("trend-show-avg");
        if (showAvgEl) {
            showAvgEl.addEventListener("change", () => {
                if (getSelectedTrendCompanies().length > 0) {
                    updateTrendPlot();
                }
            });
        }
    }

    function getSelectedTrendCurrencies() {
        const activeBtns = document.querySelectorAll(".btn-currency.active");
        const currencies = Array.from(activeBtns).map(b => b.getAttribute("data-currency"));
        return currencies.length > 0 ? currencies : ["USD"];
    }

    // Currency buttons toggle listener for Trend Tab (Multi-select support)
    const trendCurrencyBtns = document.querySelectorAll(".btn-currency");
    if (document.getElementById("trend-sector")) {
        trendCurrencyBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                btn.classList.toggle("active");
                
                // Ensure at least one currency is active
                const activeBtns = document.querySelectorAll(".btn-currency.active");
                if (activeBtns.length === 0) {
                    btn.classList.add("active");
                }
                
                const selectedCurrencies = getSelectedTrendCurrencies();
                currentCurrency = selectedCurrencies[0]; // Primary currency
                
                // Sync with global selector
                if (currencySelect) {
                    currencySelect.value = currentCurrency;
                }
                
                // If companies are selected, refresh trend features & plot
                const selected = getSelectedTrendCompanies();
                if (selected.length > 0) {
                    loadTrendFeatures();
                }
            });
        });
    }

    // Version selector is not used for Zeki Eleme trend analysis

    // Fetches the features for the first period of the company to present them as checkboxes
    // If previouslySelected is provided, re-checks those features after loading
    function loadTrendFeatures(previouslySelected) {
        const trendSector = document.getElementById("trend-sector");
        const trendFeaturesList = document.getElementById("trend-features-list");
        if (!trendSector || !trendFeaturesList) return;
        const sector = trendSector.value;
        const selectedCompanies = getSelectedTrendCompanies();
        if (selectedCompanies.length === 0) return;
        const company = selectedCompanies[0];
        const version = getSelectedTrendVersion();
        
        // Save currently selected features if not passed in
        if (!previouslySelected) {
            const checkedBoxes = trendFeaturesList.querySelectorAll("input[type='checkbox']:checked");
            previouslySelected = Array.from(checkedBoxes).map(cb => cb.value);
        }
        
        trendFeaturesList.innerHTML = '<div class="empty-state-small"><i class="fa-solid fa-circle-notch fa-spin"></i> Özellikler aranıyor...</div>';
        resetTrendChart();

        // 1. Get periods to fetch the first one
        fetch(`/api/periods?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&version=${version}`)
            .then(res => res.json())
            .then(data => {
                if (!data.periods || data.periods.length === 0) {
                    trendFeaturesList.innerHTML = '<div class="empty-state-small text-red">Dönem bulunamadı.</div>';
                    return;
                }
                const firstPeriod = data.periods[0];
                
                // 2. Load feature names from the first period
                fetch(`/api/company_features?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&period=${firstPeriod}&currency=${currentCurrency}&version=${version}`)
                    .then(res => res.json())
                    .then(featData => {
                        if (featData.error) {
                            trendFeaturesList.innerHTML = `<div class="empty-state-small text-red">${featData.error}</div>`;
                            return;
                        }
                        
                        trendFeaturesList.innerHTML = "";
                        const featureKeys = Object.keys(featData.features).sort();
                        
                        // Render Checkbox list, restoring previous selections
                        featureKeys.forEach(key => {
                            const label = document.createElement("label");
                            label.className = "feature-checkbox-label";
                            
                            const checkbox = document.createElement("input");
                            checkbox.type = "checkbox";
                            checkbox.value = key;
                            if (previouslySelected && previouslySelected.includes(key)) {
                                checkbox.checked = true;
                            }
                            checkbox.addEventListener("change", handleCheckboxChange);
                            
                            label.appendChild(checkbox);
                            label.appendChild(document.createTextNode(key));
                            trendFeaturesList.appendChild(label);
                        });
                        
                        // If we restored selections, draw the chart
                        if (previouslySelected && previouslySelected.length > 0) {
                            updateTrendPlot();
                        }
                    })
                    .catch(err => {
                        trendFeaturesList.innerHTML = `<div class="empty-state-small text-red">Hata: ${err.message}</div>`;
                    });
            })
            .catch(err => {
                trendFeaturesList.innerHTML = `<div class="empty-state-small text-red">Dönem hatası: ${err.message}</div>`;
            });
    }

    function getSelectedTrendVersion() {
        return "ZEKI_ELEME";
    }

    // Limit checkboxes to max 4 selections, and trigger plot update on change
    function handleCheckboxChange() {
        const checked = trendFeaturesList.querySelectorAll("input[type='checkbox']:checked");
        if (checked.length > 4) {
            this.checked = false;
            alert("Maksimum 4 özellik seçebilirsiniz.");
            return;
        }

        updateTrendPlot();
    }

    // Reset Chart state
    function resetTrendChart() {
        const chartPlaceholder = document.getElementById("chart-placeholder");
        const canvasContainer = document.querySelector("#tab-trend .canvas-container");
        if (!chartPlaceholder || !canvasContainer) return;
        if (trendChart) {
            trendChart.destroy();
            trendChart = null;
        }
        chartPlaceholder.style.display = "flex";
        canvasContainer.style.display = "none";
        
        const reportCard = document.getElementById("trend-report-card");
        if (reportCard) {
            reportCard.style.display = "none";
        }
    }

    // Fetch and plot line chart using Chart.js
    function updateTrendPlot() {
        const trendSector = document.getElementById("trend-sector");
        const trendFeaturesList = document.getElementById("trend-features-list");
        if (!trendSector || !trendFeaturesList) return;
        const checked = trendFeaturesList.querySelectorAll("input[type='checkbox']:checked");
        if (checked.length === 0) {
            resetTrendChart();
            return;
        }

        const sector = trendSector.value;
        const selectedCompanies = getSelectedTrendCompanies();
        if (selectedCompanies.length === 0) {
            resetTrendChart();
            return;
        }
        const version = getSelectedTrendVersion();
        const showAvg = document.getElementById("trend-show-avg").checked;
        
        // Assemble URL query
        const selectedCurrencies = getSelectedTrendCurrencies();
        let url = `/api/trend_data?sector=${encodeURIComponent(sector)}&version=${version}&show_avg=${showAvg}`;
        selectedCompanies.forEach(comp => {
            url += `&company=${encodeURIComponent(comp)}`;
        });
        selectedCurrencies.forEach(curr => {
            url += `&currency=${encodeURIComponent(curr)}`;
        });
        checked.forEach(cb => {
            url += `&features=${encodeURIComponent(cb.value)}`;
        });

        fetch(url)
            .then(res => res.json())
            .then(plotData => {
                if (plotData.error) {
                    alert(`Veri çekme hatası: ${plotData.error}`);
                    return;
                }

                chartPlaceholder.style.display = "none";
                canvasContainer.style.display = "block";

                // Setup datasets (neon style colors list)
                const colors = ['#00d2ff', '#00f27c', '#ffb300', '#ae52ff', '#ff5252', '#ff52c9', '#52ffd8', '#e2ff52', '#ff8452', '#a0a0a0'];
                const glowColors = [
                    'rgba(0, 210, 255, 0.1)',
                    'rgba(0, 242, 124, 0.1)',
                    'rgba(255, 179, 0, 0.1)',
                    'rgba(174, 82, 255, 0.1)',
                    'rgba(255, 82, 82, 0.1)',
                    'rgba(255, 82, 201, 0.1)',
                    'rgba(82, 255, 216, 0.1)',
                    'rgba(226, 255, 82, 0.1)',
                    'rgba(255, 132, 82, 0.1)',
                    'rgba(160, 160, 160, 0.1)'
                ];

                const datasets = [];
                let colorIdx = 0;

                Object.keys(plotData.data).forEach(key => {
                    const dataPoints = plotData.data[key];
                    const isAvg = key.startsWith("Sektör Ortalaması");

                    let borderColor = colors[colorIdx % colors.length];
                    let backgroundColor = glowColors[colorIdx % colors.length];
                    let borderDash = [];
                    let borderWidth = 3;

                    if (isAvg) {
                        borderColor = "#ffffff";
                        backgroundColor = "rgba(255, 255, 255, 0.05)";
                        borderDash = [6, 6];
                        borderWidth = 2;
                    }

                    datasets.push({
                        label: key,
                        data: dataPoints,
                        borderColor: borderColor,
                        backgroundColor: backgroundColor,
                        borderWidth: borderWidth,
                        borderDash: borderDash,
                        pointRadius: isAvg ? 3 : 4,
                        pointHoverRadius: isAvg ? 5 : 7,
                        tension: 0.25,
                        fill: false
                    });
                    if (!isAvg) colorIdx++;
                });

                if (trendChart) {
                    trendChart.destroy();
                }

                const canvas = document.getElementById("trend-line-chart");
                const ctx = canvas.getContext("2d");
                trendChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: plotData.periods,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#94a3b8',
                                    font: { family: 'Outfit', size: 12 }
                                }
                            },
                            tooltip: {
                                backgroundColor: '#0f1524',
                                titleFont: { family: 'Outfit', size: 13, weight: 'bold' },
                                bodyFont: { family: 'Outfit', size: 12 },
                                borderWidth: 1,
                                borderColor: 'rgba(255,255,255,0.06)'
                            }
                        },
                        scales: {
                            x: {
                                grid: { color: 'rgba(255,255,255,0.03)' },
                                ticks: {
                                    color: '#94a3b8',
                                    font: { family: 'Outfit' }
                                }
                            },
                            y: {
                                grid: { color: 'rgba(255,255,255,0.03)' },
                                ticks: {
                                    color: '#94a3b8',
                                    font: { family: 'Outfit' },
                                    callback: function(value) {
                                        return Math.round(value).toLocaleString('tr-TR');
                                    }
                                }
                            }
                        }
                    }
                });
                canvas.chartInstance = trendChart;

                // Show report card and render data
                const reportCard = document.getElementById("trend-report-card");
                if (reportCard) {
                    if (plotData.summary_stats && Object.keys(plotData.summary_stats).length > 0) {
                        reportCard.style.display = "block";
                        renderTrendReportData(plotData);
                    } else {
                        reportCard.style.display = "none";
                    }
                }
            })
            .catch(err => {
                alert(`Trend çizimi yapılamadı: ${err.message}`);
            });
    }

    function renderTrendReportData(plotData) {
        const statsGrid = document.getElementById("trend-general-stats-grid");
        const generalTableBody = document.getElementById("trend-general-table-body");
        const compPeriodsTable = document.getElementById("trend-comp-periods-table");
        const compPeriodsTableBody = document.getElementById("trend-comp-periods-table-body");
        const narrativeReportText = document.getElementById("trend-comprehensive-report-text");
        
        if (!statsGrid || !generalTableBody || !compPeriodsTable || !compPeriodsTableBody || !narrativeReportText) return;

        statsGrid.innerHTML = "";
        generalTableBody.innerHTML = "";
        compPeriodsTableBody.innerHTML = "";
        narrativeReportText.innerHTML = "";

        const currency = getSelectedTrendCurrencies()[0] || "USD";
        const features = [];
        const trendFeaturesList = document.getElementById("trend-features-list");
        if (trendFeaturesList) {
            trendFeaturesList.querySelectorAll("input[type='checkbox']:checked").forEach(cb => {
                features.push(cb.value);
            });
        }
        const mainFeat = features[0] || "Net Dönem Karı/Zararı";

        Object.keys(plotData.summary_stats).forEach(comp => {
            const compData = plotData.summary_stats[comp];
            const stats = compData.stats[mainFeat] || { sum: 0, mean: 0, max: 0, min: 0, last: 0, count: 0 };

            const card = document.createElement("div");
            card.className = "stat-item-card";
            card.innerHTML = `
                <div class="company-header">
                    <span class="company-name">${comp}</span>
                    <span class="company-rank">Sıra: #${compData.rank}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Toplam ${mainFeat}</span>
                    <span class="stat-value" style="color: var(--color-blue);">${Math.round(stats.sum).toLocaleString('tr-TR')} ${currency}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Ortalama</span>
                    <span class="stat-value">${Math.round(stats.mean).toLocaleString('tr-TR')} ${currency}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Son Çeyrek</span>
                    <span class="stat-value" style="color: var(--color-green);">${Math.round(stats.last).toLocaleString('tr-TR')} ${currency}</span>
                </div>
            `;
            statsGrid.appendChild(card);

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${comp}</strong></td>
                <td><span style="font-family: 'Fira Code'; font-weight: 600;">${Math.round(stats.sum).toLocaleString('tr-TR')} ${currency}</span></td>
                <td><span style="font-family: 'Fira Code';">${Math.round(stats.mean).toLocaleString('tr-TR')} ${currency}</span></td>
                <td><span style="font-family: 'Fira Code'; color: var(--color-green);">${Math.round(stats.max).toLocaleString('tr-TR')} ${currency}</span></td>
                <td><span style="font-family: 'Fira Code'; color: var(--color-red);">${Math.round(stats.min).toLocaleString('tr-TR')} ${currency}</span></td>
                <td><span class="badge badge-warning" style="font-size: 11px;">#${compData.rank}</span></td>
            `;
            generalTableBody.appendChild(tr);
        });

        let tableHeaderHTML = `<tr><th style="min-width: 150px;">Firma / Çeyrek</th>`;
        plotData.periods.forEach(p => {
            tableHeaderHTML += `<th>${p}. Çeyrek</th>`;
        });
        tableHeaderHTML += `</tr>`;
        compPeriodsTable.querySelector("thead").innerHTML = tableHeaderHTML;

        Object.keys(plotData.data).forEach(lineKey => {
            if (lineKey.startsWith("Sektör Ortalaması")) return;

            const tr = document.createElement("tr");
            const values = plotData.data[lineKey];

            let rowHTML = `<td><strong>${lineKey}</strong></td>`;
            values.forEach(v => {
                rowHTML += `<td><span style="font-family: 'Fira Code'; font-size: 12.5px;">${Math.round(v).toLocaleString('tr-TR')} ${currency}</span></td>`;
            });
            rowHTML += `</tr>`;
            tr.innerHTML = rowHTML;
            compPeriodsTableBody.appendChild(tr);
        });

        narrativeReportText.innerHTML = plotData.report_text;
    }

    function convertToOpacityColor(colorStr, opacity) {
        if (!colorStr) return 'rgba(255,255,255,0.2)';
        if (colorStr.startsWith('rgba')) {
            return colorStr.replace(/[\d\.]+\)$/, `${opacity})`);
        }
        if (colorStr.startsWith('rgb')) {
            return colorStr.replace('rgb', 'rgba').replace(')', `, ${opacity})`);
        }
        if (colorStr.startsWith('#')) {
            let hex = colorStr.replace('#', '');
            if (hex.length === 3) {
                hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
            }
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            return `rgba(${r}, ${g}, ${b}, ${opacity})`;
        }
        return colorStr;
    }

    // ── TAB 3: REGRESSION TREND ANALYSIS ──────────────────────────────────────
    const regTrendSector = document.getElementById("reg-trend-sector");
    const regTrendCompany = document.getElementById("reg-trend-company");
    const regTrendFeaturesList = document.getElementById("reg-trend-features-list");
    const regChartPlaceholder = document.getElementById("reg-chart-placeholder");
    const regCanvasContainer = document.getElementById("reg-canvas-container");
    const regTrendShowAvg = document.getElementById("reg-trend-show-avg");
    let regTrendChart = null;

    if (regTrendSector && regTrendCompany && regTrendFeaturesList && regChartPlaceholder && regCanvasContainer && regTrendShowAvg) {
        // Sector Selection Change
        regTrendSector.addEventListener("change", () => {
            const sector = regTrendSector.value;
            regTrendCompany.innerHTML = '<option value="">Firma Seçin...</option>';
            regTrendCompany.disabled = true;
            resetRegTrendChart();
            regTrendFeaturesList.innerHTML = '<div class="empty-state-small">Firma seçildiğinde özellikler listelenecektir.</div>';

            if (sector) {
                regTrendCompany.innerHTML = '<option value="">⏳ Firmalar yükleniyor...</option>';
                regTrendCompany.disabled = true;

                // Find the run button and disable it with a loading label while companies are being fetched
                const regRunBtn = document.getElementById("btn-run-reg-trend");
                if (regRunBtn) {
                    regRunBtn.disabled = true;
                    regRunBtn.dataset._origText = regRunBtn.textContent;
                    regRunBtn.textContent = "⏳ Veriler Çekiliyor...";
                }

                fetch(`/api/companies?sector=${encodeURIComponent(sector)}&task=regression_mape&currency=${encodeURIComponent(currentCurrency)}`)
                    .then(res => res.json())
                    .then(data => {
                        regTrendCompany.innerHTML = '<option value="">Firma Seçin...</option>';
                        regTrendCompany.disabled = false;
                        if (regRunBtn) {
                            regRunBtn.textContent = regRunBtn.dataset._origText || regRunBtn.textContent;
                            // Keep disabled until a company is actually selected
                        }
                        data.companies.forEach(comp => {
                            const opt = document.createElement("option");
                            if (typeof comp === "object") {
                                opt.value = comp.name;
                                opt.textContent = comp.label;
                            } else {
                                opt.value = comp;
                                opt.textContent = comp;
                            }
                            regTrendCompany.appendChild(opt);
                        });
                    })
                    .catch(err => {
                        regTrendCompany.innerHTML = '<option value="">⚠️ Yükleme Hatası!</option>';
                        regTrendCompany.disabled = false;
                        if (regRunBtn) {
                            regRunBtn.textContent = regRunBtn.dataset._origText || regRunBtn.textContent;
                        }
                        console.error("Regression trend firmaları yükleme hatası:", err);
                    });
            }
        });

        // Company Selection Change
        regTrendCompany.addEventListener("change", () => {
            const company = regTrendCompany.value;
            if (company) {
                updateRegTrendPlot();
            } else {
                resetRegTrendChart();
            }
        });

        // Sector Average Checkbox Change
        regTrendShowAvg.addEventListener("change", () => {
            if (regTrendCompany.value) {
                updateRegTrendPlot();
            }
        });

        // Currency Switcher buttons inside Regression Trend tab
        const regCurrencyBtns = document.querySelectorAll("#reg-currency-group .btn-currency");
        regCurrencyBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                regCurrencyBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                
                const currency = btn.getAttribute("data-currency");
                currentCurrency = currency;
                
                // Sync global dropdown
                if (currencySelect) {
                    currencySelect.value = currency;
                }
                
                // Re-load features and refresh plot
                if (regTrendCompany.value) {
                    updateRegTrendPlot();
                }
            });
        });
    }

    function loadRegTrendFeatures() {
        // No-op: we plot Net Dönem Kârı / Zararı (t) directly
    }

    // Reset Chart state
    function resetRegTrendChart() {
        const regChartPlaceholder = document.getElementById("reg-chart-placeholder");
        const regCanvasContainer = document.getElementById("reg-canvas-container");
        if (!regChartPlaceholder || !regCanvasContainer) return;
        if (regTrendChart) {
            regTrendChart.destroy();
            regTrendChart = null;
        }
        regChartPlaceholder.style.display = "flex";
        regCanvasContainer.style.display = "none";
        const commentBox = document.getElementById("reg-analysis-comment-box");
        if (commentBox) {
            commentBox.style.display = "none";
        }
    }

    // Fetch and plot line chart using Chart.js
    function updateRegTrendPlot() {
        const regTrendSector = document.getElementById("reg-trend-sector");
        const regTrendCompany = document.getElementById("reg-trend-company");
        if (!regTrendSector || !regTrendCompany) return;

        const sector = regTrendSector.value;
        const company = regTrendCompany.value;
        const feature = "Net Dönem Kârı / Zararı (t)";
        const showAvg = regTrendShowAvg.checked;

        if (!sector || !company) {
            resetRegTrendChart();
            return;
        }

        const url = `/api/regression_trend_data?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&currency=${encodeURIComponent(currentCurrency)}&feature=${encodeURIComponent(feature)}`;
        
        fetch(url)
            .then(res => res.json())
            .then(plotData => {
                if (plotData.error) {
                    alert(`Veri çekme hatası: ${plotData.error}`);
                    return;
                }

                regChartPlaceholder.style.display = "none";
                regCanvasContainer.style.display = "block";

                const datasets = [];

                // 1. Company Actual selected feature value
                datasets.push({
                    label: `${company} Gerçek ${feature}`,
                    data: plotData.company_actual,
                    borderColor: '#00f27c',
                    backgroundColor: 'rgba(0, 242, 124, 0.1)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    tension: 0.2,
                    fill: false,
                    yAxisID: 'y'
                });

                const predTrain = plotData.company_pred.map((val, index) => parseInt(plotData.periods[index]) <= 31 ? val : null);
                const predTest = plotData.company_pred.map((val, index) => parseInt(plotData.periods[index]) >= 31 ? val : null);

                // 2. Company Predicted selected feature value (Train)
                datasets.push({
                    label: `${company} Tahmini ${feature} (Eğitim)`,
                    data: predTrain,
                    borderColor: 'rgba(174, 82, 255, 0.4)',
                    backgroundColor: 'rgba(174, 82, 255, 0.1)',
                    borderWidth: 3,
                    borderDash: [5, 5],
                    pointRadius: 2,
                    pointHoverRadius: 5,
                    tension: 0.2,
                    fill: false,
                    yAxisID: 'y'
                });

                // 3. Company Predicted selected feature value (Test)
                datasets.push({
                    label: `${company} Tahmini ${feature} (Test)`,
                    data: predTest,
                    borderColor: '#ae52ff',
                    backgroundColor: 'rgba(174, 82, 255, 0.1)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    tension: 0.2,
                    fill: false,
                    yAxisID: 'y'
                });

                // 3. Sector averages if checked
                if (showAvg) {
                    datasets.push({
                        label: `Sektör Ort. Gerçek ${feature}`,
                        data: plotData.sector_avg_actual,
                        borderColor: 'rgba(255, 179, 0, 0.8)',
                        backgroundColor: 'rgba(255, 179, 0, 0.05)',
                        borderWidth: 2,
                        borderDash: [6, 6],
                        pointRadius: 2,
                        tension: 0.2,
                        fill: false,
                        yAxisID: 'y'
                    });

                    datasets.push({
                        label: `Sektör Ort. Tahmini ${feature}`,
                        data: plotData.sector_avg_pred,
                        borderColor: 'rgba(0, 210, 255, 0.8)',
                        backgroundColor: 'rgba(0, 210, 255, 0.05)',
                        borderWidth: 2,
                        borderDash: [6, 6],
                        pointRadius: 2,
                        tension: 0.2,
                        fill: false,
                        yAxisID: 'y'
                    });
                }

                if (regTrendChart) {
                    regTrendChart.destroy();
                }

                const canvas = document.getElementById("reg-trend-line-chart");
                const ctx = canvas.getContext("2d");
                regTrendChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: plotData.periods,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#94a3b8',
                                    font: { family: 'Outfit', size: 11 }
                                }
                            },
                            tooltip: {
                                backgroundColor: '#0f1524',
                                titleFont: { family: 'Outfit', size: 13, weight: 'bold' },
                                bodyFont: { family: 'Outfit', size: 12 },
                                borderWidth: 1,
                                borderColor: 'rgba(255,255,255,0.06)'
                            }
                        },
                        scales: {
                            x: {
                                grid: { color: 'rgba(255,255,255,0.03)' },
                                ticks: {
                                    color: '#94a3b8',
                                    font: { family: 'Outfit' }
                                }
                            },
                            y: {
                                position: 'left',
                                grid: { color: 'rgba(255,255,255,0.03)' },
                                ticks: {
                                    color: '#94a3b8',
                                    font: { family: 'Outfit' },
                                    callback: function(value) {
                                        return Math.round(value).toLocaleString('tr-TR');
                                    }
                                },
                                title: {
                                    display: true,
                                    text: `${feature} Değeri (${currentCurrency})`,
                                    color: '#94a3b8',
                                    font: { family: 'Outfit', size: 12, weight: 'bold' }
                                }
                            }
                        }
                    }
                });
                canvas.chartInstance = regTrendChart;

                // Render dynamic text commentary
                const commentBox = document.getElementById("reg-analysis-comment-box");
                const commentText = document.getElementById("reg-analysis-comment-text");
                if (commentBox && commentText) {
                     commentText.innerHTML = plotData.analysis_comment || "Yorum oluşturulamadı.";
                     commentBox.style.display = "block";
                }
            })
            .catch(err => {
                alert(`Regresyon trend grafiği çizilemedi: ${err.message}`);
            });
    }

    // ── SECTOR NAME CLEANER HELPER ──────────────────────────────────────────
    function cleanSectorName(sector) {
        if (!sector) return "";
        const s = sector.toUpperCase();
        if (s.includes("SANAY") || s.includes("MALAT")) return "Sanayi ve İmalat";
        if (s.includes("FINANS") || s.includes("YATIRIM") || s.includes("FNANS")) return "Finans ve Yatırım";
        if (s.includes("NSAAT") || s.includes("GAYR") || s.includes("NSAT")) return "İnşaat ve Gayrimenkul";
        if (s.includes("TEKNO") || s.includes("HZMET") || s.includes("HIZMET")) return "Teknoloji ve Hizmet";
        if (s.includes("GIDA") || s.includes("TARIM")) return "Gıda ve Tarım";
        if (s.includes("ENERJ")) return "Enerji ve Hammadde";
        if (s.includes("TCARET") || s.includes("TICARET") || s.includes("PAZAR") || s.includes("HIZMETLER") || s.includes("HZMETLER")) return "Ticaret ve Pazarlama";
        if (s.includes("ORTALAMA") || s.includes("GENEL")) return "Ortalama / Genel";
        return sector.replace(/_/g, " ");
    }

    // ── MODEL NAME SHORTER HELPER ────────────────────────────────────────────
    function shortModelName(model) {
        if (!model) return "-";
        return model
            .replace("Classifier", "")
            .replace("Regressor", "")
            .replace("RandomForest", "Random Forest")
            .replace("ExtraTrees", "Extra Trees")
            .replace("LightGBM", "LGBM")
            .replace("GradientBoosting", "GBR")
            .replace("LinearRegression", "Linear Reg.")
            .replace("LogisticRegression", "Logistic Reg.")
            .replace(/_/g, " ");
    }

    // ── TAB 1: ACADEMIC MATRICES & NOTES ─────────────────────────────────────
    function loadJigsawPerformance() {
        const jigsawTable = document.getElementById("jigsaw-table");
        if (!jigsawTable) return;
        const tbody = jigsawTable.querySelector("tbody");
        const compTable = document.getElementById("comparison-summary-table");
        const compTbody = compTable ? compTable.querySelector("tbody") : null;
        
        const v1Table = document.getElementById("v1-metrics-table");
        const v2Table = document.getElementById("v2-metrics-table");
        if (!v1Table || !v2Table) return;
        const v1Tbody = v1Table.querySelector("tbody");
        const v2Tbody = v2Table.querySelector("tbody");
        
        tbody.innerHTML = '<tr><td colspan="11" class="text-center"><i class="fa-solid fa-circle-notch fa-spin"></i> Karar matrisi yükleniyor...</td></tr>';
        if (compTbody) {
            compTbody.innerHTML = '<tr><td colspan="9" class="text-center"><i class="fa-solid fa-circle-notch fa-spin"></i> Karşılaştırma özeti yükleniyor...</td></tr>';
        }
        v1Tbody.innerHTML = '<tr><td colspan="7" class="text-center"><i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor...</td></tr>';
        v2Tbody.innerHTML = '<tr><td colspan="7" class="text-center"><i class="fa-solid fa-circle-notch fa-spin"></i> Yükleniyor...</td></tr>';

        fetch(`/api/metrics?currency=${currentCurrency}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    tbody.innerHTML = `<tr><td colspan="11" class="text-center text-red">${data.error}</td></tr>`;
                    if (compTbody) compTbody.innerHTML = `<tr><td colspan="9" class="text-center text-red">${data.error}</td></tr>`;
                    v1Tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red">${data.error}</td></tr>`;
                    v2Tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red">${data.error}</td></tr>`;
                    return;
                }

                // Show/hide currency fallback banner dynamically
                const banner = document.getElementById("metrics-fallback-banner");
                if (banner) {
                    if (data.fallback) {
                        banner.style.display = "flex";
                        const reqEl = document.getElementById("fallback-requested-curr");
                        if (reqEl) reqEl.textContent = data.requested_currency || currentCurrency;
                    } else {
                        banner.style.display = "none";
                    }
                }

                // 1. Calculate dynamic KPI values from best_jigsaw
                const activeSectors = data.best_jigsaw.filter(row => {
                    const s = row["Sektör"] || row["Sektor"];
                    return s && s !== "ORTALAMA" && s !== "ORTALAMA / GENEL";
                });

                // KPI 1: Ortalama Hibrit WMAPE
                let hybridWmapeSum = 0;
                let hybridWmapeCount = 0;
                activeSectors.forEach(row => {
                    const sName = cleanSectorName(row["Sektör"] || row["Sektor"]);
                    const version = row["Reg_Sayısal_Versiyon"];
                    const metrics = (version === "V1") ? data.v1_metrics : data.v2_metrics;
                    if (metrics) {
                        const match = metrics.find(m => cleanSectorName(m["Sektor"] || m["Sektör"]) === sName);
                        if (match && match["WMAPE (%)"] != null) {
                            hybridWmapeSum += match["WMAPE (%)"];
                            hybridWmapeCount++;
                        }
                    }
                });
                const avgHybridWmape = hybridWmapeCount > 0 ? (hybridWmapeSum / hybridWmapeCount) : 0;
                const kpiWmapeEl = document.getElementById("kpi-avg-wmape");
                if (kpiWmapeEl) kpiWmapeEl.textContent = `%${avgHybridWmape.toFixed(1)}`;
                
                const kpiWmapeDetailEl = document.getElementById("kpi-avg-wmape-detail");
                if (kpiWmapeDetailEl) kpiWmapeDetailEl.textContent = `%${avgHybridWmape.toFixed(2)}`;

                // KPI 2: Ortalama Sınıflandırma Başarısı
                let clsAccSum = 0;
                let clsAccCount = 0;
                let clsKzSum = 0;
                let clsKzCount = 0;
                let clsYonSum = 0;
                let clsYonCount = 0;
                activeSectors.forEach(row => {
                    const kz = row["Cls_KZ_Skor (%)"];
                    const yon = row["Cls_Yön_Skor (%)"] || row["Cls_Yon_Skor (%)"];
                    if (kz != null && yon != null) {
                        clsAccSum += (kz + yon) / 2;
                        clsAccCount++;
                    }
                    if (kz != null) {
                        clsKzSum += kz;
                        clsKzCount++;
                    }
                    if (yon != null) {
                        clsYonSum += yon;
                        clsYonCount++;
                    }
                });
                const avgClsAcc = clsAccCount > 0 ? (clsAccSum / clsAccCount) : 0;
                const kpiClsEl = document.getElementById("kpi-avg-cls-acc");
                if (kpiClsEl) kpiClsEl.textContent = `%${avgClsAcc.toFixed(1)}`;
                
                const summaryAccEl = document.getElementById("dynamic-summary-accuracy");
                if (summaryAccEl) summaryAccEl.textContent = `%${avgClsAcc.toFixed(1)}`;
                
                const summaryCurrEl = document.getElementById("summary-currency-text");
                if (summaryCurrEl) summaryCurrEl.textContent = currentCurrency;
                
                const kpiClsKzDetail = document.getElementById("kpi-avg-cls-kz-detail");
                if (kpiClsKzDetail) kpiClsKzDetail.textContent = `%${(clsKzCount > 0 ? (clsKzSum / clsKzCount) : 0).toFixed(2)}`;
                
                const kpiClsYonDetail = document.getElementById("kpi-avg-cls-yon-detail");
                if (kpiClsYonDetail) kpiClsYonDetail.textContent = `%${(clsYonCount > 0 ? (clsYonSum / clsYonCount) : 0).toFixed(2)}`;
                
                const kpiTotalCosDetail = document.getElementById("kpi-total-cos-detail");
                if (kpiTotalCosDetail) kpiTotalCosDetail.textContent = "376 Firma";

                // Update dynamic currency labels
                document.querySelectorAll(".dynamic-currency-label").forEach(lbl => {
                    lbl.textContent = currentCurrency;
                });

                // Populate dynamic regression bars
                const regBarsContainer = document.getElementById("dynamic-regression-bars");
                if (regBarsContainer) {
                    regBarsContainer.innerHTML = "";
                    const activeRegSectors = data.best_jigsaw.filter(row => {
                        const s = row["Sektör"] || row["Sektor"];
                        return s && s !== "ORTALAMA" && s !== "ORTALAMA / GENEL";
                    });
                    activeRegSectors.forEach((row, i) => {
                        const sectName = row["Sektör"] || row["Sektor"];
                        const cleanedName = cleanSectorName(sectName);
                        const displayName = getSectorDisplayName(cleanedName);
                        const score = parseFloat(row["Reg_Sayısal_Skor (%)"] || 0);
                        const colors = ["", "purple", "gold", "green", "blue", "orange", "pink"];
                        const colorClass = colors[i % colors.length];
                        
                        const barItem = document.createElement("div");
                        barItem.className = "insight-bar-item";
                        barItem.innerHTML = `
                            <div class="insight-bar-label">
                                <span>${displayName}</span>
                                <strong>%${score.toFixed(2)}</strong>
                            </div>
                            <div class="insight-bar-wrapper">
                                <div class="insight-bar-fill ${colorClass}" style="width: ${Math.min(100, Math.max(0, score))}%"></div>
                            </div>
                        `;
                        regBarsContainer.appendChild(barItem);
                    });
                }

                // KPI 3: Şampiyon Model V2 / V1 Oranı
                let v1Count = 0;
                let v2Count = 0;
                activeSectors.forEach(row => {
                    const cols = ["Reg_Sayısal_Versiyon", "Reg_Yön_Versiyon", "Reg_KZ_Versiyon", "Cls_Yön_Versiyon", "Cls_KZ_Versiyon"];
                    cols.forEach(col => {
                        const val = row[col];
                        if (val === "V1") v1Count++;
                        else if (val === "V2") v2Count++;
                    });
                });
                const totalModels = v1Count + v2Count;
                const v2Pct = totalModels > 0 ? ((v2Count / totalModels) * 100).toFixed(1) : "0.0";
                const v1Pct = totalModels > 0 ? ((v1Count / totalModels) * 100).toFixed(1) : "0.0";
                const kpiRatioEl = document.getElementById("kpi-model-ratio");
                if (kpiRatioEl) kpiRatioEl.textContent = `%${v2Pct} / %${v1Pct}`;
                
                const kpiRatioDetailEl = document.getElementById("kpi-model-ratio-detail");
                if (kpiRatioDetailEl) kpiRatioDetailEl.textContent = `%${v2Pct} / %${v1Pct}`;

                // 2. Populate Jigsaw Matrix Table rows
                tbody.innerHTML = "";
                data.best_jigsaw.forEach(row => {
                    const tr = document.createElement("tr");
                    if (row["Sektör"] === "ORTALAMA / GENEL" || row["Sektor"] === "ORTALAMA / GENEL" || row["Sektör"] === "ORTALAMA" || row["Sektor"] === "ORTALAMA") {
                        tr.className = "avg-row-highlight";
                    }

                    // Sector label
                    const tdSect = document.createElement("td");
                    const cleanedName = cleanSectorName(row["Sektör"] || row["Sektor"]);
                    tdSect.textContent = getSectorDisplayName(cleanedName);
                    tr.appendChild(tdSect);

                    // Version & Jigsaw Score mappings
                    const colPairs = [
                        { ver: "Reg_Sayısal_Versiyon", score: "Reg_Sayısal_Skor (%)" },
                        { ver: "Reg_Yön_Versiyon", score: "Reg_Yön_Skor (%)" },
                        { ver: "Reg_KZ_Versiyon", score: "Reg_KZ_Skor (%)" },
                        { ver: "Cls_Yön_Versiyon", score: "Cls_Yön_Skor (%)" },
                        { ver: "Cls_KZ_Versiyon", score: "Cls_KZ_Skor (%)" }
                    ];

                    colPairs.forEach(pair => {
                        const version = row[pair.ver] || "-";
                        const score = row[pair.score];

                        const tdVer = document.createElement("td");
                        tdVer.textContent = version;
                        if (version === "V1") tdVer.className = "v1-cell";
                        else if (version === "V2") tdVer.className = "v2-cell";
                        tr.appendChild(tdVer);

                        const tdScore = document.createElement("td");
                        tdScore.textContent = score != null ? `${score.toFixed(1)}%` : "-";
                        tr.appendChild(tdScore);
                    });

                    tbody.appendChild(tr);
                });

                // 3. Populate V1 vs V2 Comparison Summary Table
                if (compTbody) {
                    compTbody.innerHTML = "";
                    if (data.comparison && data.comparison.length > 0) {
                        let sumW1 = 0, sumW2 = 0;
                        let sumKz1 = 0, sumKz2 = 0;
                        let sumY1 = 0, sumY2 = 0;
                        let validCount = 0;

                        data.comparison.forEach(row => {
                            const tr = document.createElement("tr");
                            const sectName = row["Sektor"] || row["Sektör"];
                            
                            // Compare WMAPEs (lower is better)
                            const w1 = row["v1_Reg_WMAPE"];
                            const w2 = row["v2_Reg_WMAPE"];
                            let w1Class = "", w2Class = "";
                            if (w1 != null && w2 != null) {
                                if (w1 < w2) w1Class = "best-cell-highlight";
                                else w2Class = "best-cell-highlight";
                                sumW1 += w1;
                                sumW2 += w2;
                            }

                            // Compare K/Z Acc (higher is better)
                            const kz1 = row["v1_Cls_KZ_Acc"];
                            const kz2 = row["v2_Cls_KZ_Acc"];
                            let kz1Class = "", kz2Class = "";
                            if (kz1 != null && kz2 != null) {
                                const factor1 = kz1 <= 1 ? 100 : 1;
                                const factor2 = kz2 <= 1 ? 100 : 1;
                                const v_kz1 = kz1 * factor1;
                                const v_kz2 = kz2 * factor2;
                                if (v_kz1 > v_kz2) kz1Class = "best-cell-highlight";
                                else kz2Class = "best-cell-highlight";
                                sumKz1 += v_kz1;
                                sumKz2 += v_kz2;
                            }

                            // Compare Yön Acc (higher is better)
                            const y1 = row["v1_Cls_Yön_Acc"] || row["v1_Cls_Yon_Acc"];
                            const y2 = row["v2_Cls_Yön_Acc"] || row["v2_Cls_Yon_Acc"];
                            let y1Class = "", y2Class = "";
                            if (y1 != null && y2 != null) {
                                const factor1 = y1 <= 1 ? 100 : 1;
                                const factor2 = y2 <= 1 ? 100 : 1;
                                const v_y1 = y1 * factor1;
                                const v_y2 = y2 * factor2;
                                if (v_y1 > v_y2) y1Class = "best-cell-highlight";
                                else y2Class = "best-cell-highlight";
                                sumY1 += v_y1;
                                sumY2 += v_y2;
                            }
                            
                            validCount++;

                            tr.innerHTML = `
                                <td><strong>${cleanSectorName(sectName)}</strong></td>
                                <td>${shortModelName(row["v1_Reg_Model"])}</td>
                                <td>${shortModelName(row["v2_Reg_Model"])}</td>
                                <td class="${w1Class}">${w1 != null ? w1.toFixed(2) + '%' : "-"}</td>
                                <td class="${w2Class}">${w2 != null ? w2.toFixed(2) + '%' : "-"}</td>
                                <td class="${kz1Class}">${kz1 != null ? (kz1 * (kz1 <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                                <td class="${kz2Class}">${kz2 != null ? (kz2 * (kz2 <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                                <td class="${y1Class}">${y1 != null ? (y1 * (y1 <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                                <td class="${y2Class}">${y2 != null ? (y2 * (y2 <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                            `;
                            compTbody.appendChild(tr);
                        });

                        // Calculate and append the dynamic ORTALAMA/GENEL row
                        if (validCount > 0) {
                            const avgW1 = sumW1 / validCount;
                            const avgW2 = sumW2 / validCount;
                            const avgKz1 = sumKz1 / validCount;
                            const avgKz2 = sumKz2 / validCount;
                            const avgY1 = sumY1 / validCount;
                            const avgY2 = sumY2 / validCount;

                            let w1Class = "", w2Class = "";
                            if (avgW1 < avgW2) w1Class = "best-cell-highlight";
                            else w2Class = "best-cell-highlight";

                            let kz1Class = "", kz2Class = "";
                            if (avgKz1 > avgKz2) kz1Class = "best-cell-highlight";
                            else kz2Class = "best-cell-highlight";

                            let y1Class = "", y2Class = "";
                            if (avgY1 > avgY2) y1Class = "best-cell-highlight";
                            else y2Class = "best-cell-highlight";

                            const trAvg = document.createElement("tr");
                            trAvg.className = "avg-row-highlight";
                            trAvg.innerHTML = `
                                <td><strong>ORTALAMA / GENEL</strong></td>
                                <td>-</td>
                                <td>-</td>
                                <td class="${w1Class}">${avgW1.toFixed(2)}%</td>
                                <td class="${w2Class}">${avgW2.toFixed(2)}%</td>
                                <td class="${kz1Class}">${avgKz1.toFixed(1)}%</td>
                                <td class="${kz2Class}">${avgKz2.toFixed(1)}%</td>
                                <td class="${y1Class}">${avgY1.toFixed(1)}%</td>
                                <td class="${y2Class}">${avgY2.toFixed(1)}%</td>
                            `;
                            compTbody.appendChild(trAvg);
                        }
                    } else {
                        compTbody.innerHTML = '<tr><td colspan="9" class="text-center">Veri bulunamadı</td></tr>';
                    }
                }

                // 4. Populate V1 Table
                v1Tbody.innerHTML = "";
                if (data.v1_metrics && data.v1_metrics.length > 0) {
                    data.v1_metrics.forEach(row => {
                        const tr = document.createElement("tr");
                        if (row["Sektor"] === "ORTALAMA / GENEL" || row["Sektör"] === "ORTALAMA / GENEL") {
                            tr.className = "avg-row-highlight";
                        }
                        
                        tr.innerHTML = `
                            <td><strong>${cleanSectorName(row["Sektor"] || row["Sektör"])}</strong></td>
                            <td>${shortModelName(row["Reg_Model"])}</td>
                            <td>${row["WMAPE (%)"] != null ? row["WMAPE (%)"].toFixed(2) + '%' : "-"}</td>
                            <td>${shortModelName(row["Cls_Kar_Zarar_Tahmini_Model"])}</td>
                            <td>${row["Cls_Kar_Zarar_Tahmini_Acc"] != null ? (row["Cls_Kar_Zarar_Tahmini_Acc"] * (row["Cls_Kar_Zarar_Tahmini_Acc"] <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                            <td>${shortModelName(row["Cls_Yon_Tahmini_Model"])}</td>
                            <td>${row["Cls_Yon_Tahmini_Acc"] != null ? (row["Cls_Yon_Tahmini_Acc"] * (row["Cls_Yon_Tahmini_Acc"] <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                        `;
                        v1Tbody.appendChild(tr);
                    });
                } else {
                    v1Tbody.innerHTML = '<tr><td colspan="7" class="text-center">Veri bulunamadı</td></tr>';
                }

                // 5. Populate V2 Table
                v2Tbody.innerHTML = "";
                if (data.v2_metrics && data.v2_metrics.length > 0) {
                    data.v2_metrics.forEach(row => {
                        const tr = document.createElement("tr");
                        if (row["Sektor"] === "ORTALAMA / GENEL" || row["Sektör"] === "ORTALAMA / GENEL") {
                            tr.className = "avg-row-highlight";
                        }
                        
                        tr.innerHTML = `
                            <td><strong>${cleanSectorName(row["Sektor"] || row["Sektör"])}</strong></td>
                            <td>${shortModelName(row["Reg_Model"])}</td>
                            <td>${row["WMAPE (%)"] != null ? row["WMAPE (%)"].toFixed(2) + '%' : "-"}</td>
                            <td>${shortModelName(row["Cls_Kar_Zarar_Tahmini_Model"])}</td>
                            <td>${row["Cls_Kar_Zarar_Tahmini_Acc"] != null ? (row["Cls_Kar_Zarar_Tahmini_Acc"] * (row["Cls_Kar_Zarar_Tahmini_Acc"] <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                            <td>${shortModelName(row["Cls_Yon_Tahmini_Model"])}</td>
                            <td>${row["Cls_Yon_Tahmini_Acc"] != null ? (row["Cls_Yon_Tahmini_Acc"] * (row["Cls_Yon_Tahmini_Acc"] <= 1 ? 100 : 1)).toFixed(1) + '%' : "-"}</td>
                        `;
                        v2Tbody.appendChild(tr);
                    });
                } else {
                    v2Tbody.innerHTML = '<tr><td colspan="7" class="text-center">Veri bulunamadı</td></tr>';
                }
            })
            .catch(err => {
                tbody.innerHTML = `<tr><td colspan="11" class="text-center text-red">Yükleme hatası: ${err.message}</td></tr>`;
                if (compTbody) compTbody.innerHTML = `<tr><td colspan="9" class="text-center text-red">Yükleme hatası</td></tr>`;
                v1Tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red">Yükleme hatası</td></tr>`;
                v2Tbody.innerHTML = `<tr><td colspan="7" class="text-center text-red">Yükleme hatası</td></tr>`;
            });
    }

    // ── NUMERIC FORMATTER HELPER ─────────────────────────────────────────────
    function formatNumber(num) {
        if (num == null || isNaN(num)) return "-";
        return num.toLocaleString('tr-TR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // ── ADMIN PANEL SECURITY & LOGIN ─────────────────────────────────────────
    let isAdminAuthenticated = false;

    function setupAdminPanel() {
        const btnLogin = document.getElementById("btn-admin-login");
        const btnLogout = document.getElementById("btn-admin-logout");
        const usernameInput = document.getElementById("admin-username");
        const passwordInput = document.getElementById("admin-password");
        const loginError = document.getElementById("admin-login-error");
        const lockScreen = document.getElementById("admin-lock-screen");
        const secureContent = document.getElementById("admin-secure-content");

        if (!btnLogin) return;

        // Login trigger
        btnLogin.addEventListener("click", () => {
            const usernameVal = usernameInput.value.trim().toLowerCase();
            const passwordVal = passwordInput.value;

            // Check against database.js credentials (ADMIN_CREDENTIALS)
            const targetUser = ADMIN_CREDENTIALS.username.toLowerCase();
            const targetUserAlt = ADMIN_CREDENTIALS.usernameAlt.toLowerCase();
            const targetPass = ADMIN_CREDENTIALS.password;

            if ((usernameVal === targetUser || usernameVal === targetUserAlt) && passwordVal === targetPass) {
                isAdminAuthenticated = true;
                loginError.style.display = "none";
                lockScreen.style.display = "none";
                secureContent.style.display = "block";
                
                // Change sidebar nav icon to unlocked
                const adminIcon = document.querySelector('.nav-item[data-tab="admin"] i');
                if (adminIcon) {
                    adminIcon.className = "fa-solid fa-lock-open";
                }
            } else {
                loginError.style.display = "block";
            }
        });

        // Logout trigger
        btnLogout.addEventListener("click", () => {
            isAdminAuthenticated = false;
            usernameInput.value = "";
            passwordInput.value = "";
            loginError.style.display = "none";
            lockScreen.style.display = "block";
            secureContent.style.display = "none";

            // Change sidebar nav icon back to locked
            const adminIcon = document.querySelector('.nav-item[data-tab="admin"] i');
            if (adminIcon) {
                adminIcon.className = "fa-solid fa-lock";
            }
        });

        // Enter key listeners
        const handleEnterKey = (e) => {
            if (e.key === "Enter") {
                btnLogin.click();
            }
        };
        usernameInput.addEventListener("keydown", handleEnterKey);
        passwordInput.addEventListener("keydown", handleEnterKey);
    }

    // ── LIGHTBOX MODAL EVENT HANDLERS ───────────────────────────────────────
    const setupLightbox = () => {
        const lightbox = document.getElementById("image-lightbox");
        const lightboxImg = document.getElementById("lightbox-img");
        const lightboxCaption = document.getElementById("lightbox-caption");
        const closeBtn = document.querySelector(".lightbox-close");

        if (lightbox && lightboxImg) {
            document.querySelectorAll(".zoomable-img").forEach(img => {
                img.addEventListener("click", function() {
                    lightbox.style.display = "flex";
                    lightboxImg.src = this.src;
                    lightboxCaption.textContent = this.alt;
                });
            });

            const closeLightbox = () => {
                lightbox.style.display = "none";
            };

            if (closeBtn) {
                closeBtn.addEventListener("click", closeLightbox);
            }
            lightbox.addEventListener("click", function(e) {
                if (e.target === lightbox || e.target === closeBtn) {
                    closeLightbox();
                }
            });
            document.addEventListener("keydown", function(e) {
                if (e.key === "Escape" && lightbox.style.display === "flex") {
                    closeLightbox();
                }
            });
        }
    };

    // ── CLASSIFIER TREND CHARTS SYSTEM ───────────────────────────────────────
    function hideClassifierChart(prefix) {
        const chartCard = document.getElementById(`${prefix}-chart-card`);
        if (chartCard) {
            chartCard.style.display = "none";
        }
        if (prefix === "kz" && kzTrendChart) {
            kzTrendChart.destroy();
            kzTrendChart = null;
        }
        if (prefix === "dir" && dirTrendChart) {
            dirTrendChart.destroy();
            dirTrendChart = null;
        }
    }

    function renderCustomLegend(prefix, chartInstance) {
        const legendContainer = document.getElementById(`${prefix}-custom-legend`);
        if (!legendContainer) return;
        legendContainer.innerHTML = "";

        chartInstance.data.datasets.forEach((dataset, index) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "legend-item-btn";
            btn.dataset.datasetIndex = index;
            
            const circle = document.createElement("span");
            circle.className = "legend-circle";
            
            const isVisible = chartInstance.isDatasetVisible(index);
            circle.style.backgroundColor = isVisible ? dataset.borderColor : "rgba(148, 163, 184, 0.2)";
            circle.style.border = `2px solid ${dataset.borderColor}`;
            
            const labelSpan = document.createElement("span");
            labelSpan.textContent = dataset.label;
            labelSpan.style.color = isVisible ? "#ffffff" : "#64748b";
            labelSpan.style.fontWeight = isVisible ? "600" : "400";

            btn.appendChild(circle);
            btn.appendChild(labelSpan);

            btn.addEventListener("click", () => {
                const currentlyVisible = chartInstance.isDatasetVisible(index);
                if (currentlyVisible) {
                    chartInstance.hide(index);
                    circle.style.backgroundColor = "rgba(148, 163, 184, 0.2)";
                    labelSpan.style.color = "#64748b";
                    labelSpan.style.fontWeight = "400";
                } else {
                    chartInstance.show(index);
                    circle.style.backgroundColor = dataset.borderColor;
                    labelSpan.style.color = "#ffffff";
                    labelSpan.style.fontWeight = "600";
                }
            });

            legendContainer.appendChild(btn);
        });
    }

    function loadClassifierTrendChart(prefix, sector, company) {
        const chartCard = document.getElementById(`${prefix}-chart-card`);
        if (!chartCard) return;
        const canvasId = `${prefix}-trend-line-chart`;
        const canvasEl = document.getElementById(canvasId);
        if (!canvasEl) return;
        
        const ctx = canvasEl.getContext("2d");

        // Set up error periods from prediction outcomes
        const errorPeriods = new Set();
        const rawResults = canvasEl.dataset.results;
        if (rawResults) {
            try {
                const results = JSON.parse(rawResults);
                results.forEach(r => {
                    const isCorrect = prefix === "kz" ? (r.pred_kz === r.actual_kz) : (r.pred_yon === r.actual_yon);
                    const hasActual = prefix === "kz" ? (r.actual_kz !== null && r.actual_kz !== undefined) : (r.actual_yon !== null && r.actual_yon !== undefined);
                    if (hasActual && !isCorrect) {
                        errorPeriods.add(`${r.period}. Çeyrek`);
                    }
                });
            } catch (e) {
                console.error("Failed to parse results for error highlighting:", e);
            }
        }

        fetch(`/api/competitor_analysis?sector=${encodeURIComponent(sector)}&company=${encodeURIComponent(company)}&currency=${currentCurrency}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    console.error("Failed to load classifier trend data:", data.error);
                    chartCard.style.display = "none";
                    return;
                }

                chartCard.style.display = "block";

                if (prefix === "kz" && kzTrendChart) {
                    kzTrendChart.destroy();
                    kzTrendChart = null;
                } else if (prefix === "dir" && dirTrendChart) {
                    dirTrendChart.destroy();
                    dirTrendChart = null;
                }

                const labels = data.periods_data.map(p => `${p.period}. Çeyrek`);
                const companyValues = data.periods_data.map(p => p.company_value);
                
                const companyPredValuesTrain = data.periods_data.map((p, idx) => {
                    if (idx === 0) return null;
                    const prevP = data.periods_data[idx - 1];
                    return p.period <= 31 ? (prevP.company_pred_value || 0.0) : null;
                });
                const companyPredValuesTest = data.periods_data.map((p, idx) => {
                    if (idx === 0) return null;
                    const prevP = data.periods_data[idx - 1];
                    return p.period >= 31 ? (prevP.company_pred_value || 0.0) : null;
                });
                
                const sectorAverages = data.periods_data.map(p => p.sector_avg);
                const sectorMedians = data.periods_data.map(p => p.sector_median);

                const getPointColor = (baseColor, dimColor) => (ctx) => {
                    const label = ctx.chart.data.labels[ctx.dataIndex];
                    const isHighlight = canvasEl.dataset.highlightErrors === "true";
                    if (isHighlight) {
                        return errorPeriods.has(label) ? baseColor : dimColor;
                    }
                    return baseColor;
                };

                const getSegmentColor = (baseColor, dimColor) => (ctx) => {
                    const isHighlight = canvasEl.dataset.highlightErrors === "true";
                    if (isHighlight) {
                        const label2 = ctx.chart.data.labels[ctx.p1.parsed.x];
                        return errorPeriods.has(label2) ? baseColor : dimColor;
                    }
                    return baseColor;
                };

                const newChart = new Chart(ctx, {
                    type: "line",
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: `${company} Net Dönem Kârı (t)`,
                                data: companyValues,
                                borderColor: '#ffb300',
                                backgroundColor: 'rgba(255, 179, 0, 0.1)',
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 7,
                                tension: 0.2,
                                fill: false,
                                pointBackgroundColor: getPointColor('#ffb300', 'rgba(255, 179, 0, 0.2)'),
                                pointBorderColor: getPointColor('#ffb300', 'rgba(255, 179, 0, 0.2)'),
                                segment: {
                                    borderColor: getSegmentColor('#ffb300', 'rgba(255, 179, 0, 0.2)')
                                }
                            },
                            {
                                label: `${company} Tahmini Kârı (Eğitim Dönemi)`,
                                data: companyPredValuesTrain,
                                borderColor: 'rgba(174, 82, 255, 0.4)',
                                backgroundColor: 'rgba(174, 82, 255, 0.1)',
                                borderWidth: 3,
                                borderDash: [5, 5],
                                pointRadius: 2,
                                pointHoverRadius: 5,
                                tension: 0.2,
                                fill: false,
                                pointBackgroundColor: getPointColor('rgba(174, 82, 255, 0.4)', 'rgba(174, 82, 255, 0.08)'),
                                pointBorderColor: getPointColor('rgba(174, 82, 255, 0.4)', 'rgba(174, 82, 255, 0.08)'),
                                segment: {
                                    borderColor: getSegmentColor('rgba(174, 82, 255, 0.4)', 'rgba(174, 82, 255, 0.08)')
                                }
                            },
                            {
                                label: `${company} Tahmini Kârı (Test Dönemi)`,
                                data: companyPredValuesTest,
                                borderColor: '#ae52ff',
                                backgroundColor: 'rgba(174, 82, 255, 0.1)',
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 7,
                                tension: 0.2,
                                fill: false,
                                pointBackgroundColor: getPointColor('#ae52ff', 'rgba(174, 82, 255, 0.2)'),
                                pointBorderColor: getPointColor('#ae52ff', 'rgba(174, 82, 255, 0.2)'),
                                segment: {
                                    borderColor: getSegmentColor('#ae52ff', 'rgba(174, 82, 255, 0.2)')
                                }
                            },
                            {
                                label: "Sektör Ortalaması",
                                data: sectorAverages,
                                borderColor: '#00d2ff',
                                backgroundColor: 'rgba(0, 210, 255, 0.05)',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                pointRadius: 3,
                                tension: 0.2,
                                fill: false,
                                pointBackgroundColor: getPointColor('#00d2ff', 'rgba(0, 210, 255, 0.2)'),
                                pointBorderColor: getPointColor('#00d2ff', 'rgba(0, 210, 255, 0.2)'),
                                segment: {
                                    borderColor: getSegmentColor('#00d2ff', 'rgba(0, 210, 255, 0.2)')
                                }
                            },
                            {
                                label: "Sektör Medyanı",
                                data: sectorMedians,
                                borderColor: '#00f27c',
                                backgroundColor: 'rgba(0, 242, 124, 0.05)',
                                borderWidth: 2,
                                borderDash: [2, 2],
                                pointRadius: 3,
                                tension: 0.2,
                                fill: false,
                                pointBackgroundColor: getPointColor('#00f27c', 'rgba(0, 242, 124, 0.2)'),
                                pointBorderColor: getPointColor('#00f27c', 'rgba(0, 242, 124, 0.2)'),
                                segment: {
                                    borderColor: getSegmentColor('#00f27c', 'rgba(0, 242, 124, 0.2)')
                                }
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false // Disabled in favor of custom circular legend
                            },
                            tooltip: {
                                backgroundColor: '#0f1524',
                                titleFont: { family: 'Outfit', size: 13, weight: 'bold' },
                                bodyFont: { family: 'Outfit', size: 12 },
                                borderWidth: 1,
                                borderColor: 'rgba(255,255,255,0.06)',
                                callbacks: {
                                    label: function(context) {
                                        let val = context.raw;
                                        return `${context.dataset.label}: ${Math.round(val).toLocaleString('tr-TR')} ${currentCurrency}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                grid: {
                                    color: "rgba(255, 255, 255, 0.04)"
                                },
                                ticks: {
                                    color: "#94a3b8",
                                    font: { family: 'Outfit', size: 11 },
                                    callback: function(value) {
                                        if (Math.abs(value) >= 1e6) {
                                            return (value / 1e6).toFixed(1) + "M";
                                        } else if (Math.abs(value) >= 1e3) {
                                            return (value / 1e3).toFixed(0) + "K";
                                        }
                                        return value;
                                    }
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    color: "#94a3b8",
                                    font: { family: 'Outfit', size: 11 }
                                }
                            }
                        }
                    }
                });

                canvasEl.chartInstance = newChart;

                if (prefix === "kz") {
                    kzTrendChart = newChart;
                } else {
                    dirTrendChart = newChart;
                }

                // Render custom HTML circular legend buttons
                renderCustomLegend(prefix, newChart);
            })
            .catch(err => {
                console.error("Error loading classifier trend chart:", err);
                chartCard.style.display = "none";
            });
    }

    setupLightbox();

    // Initialize Admin Panel Listeners
    setupAdminPanel();

    // ── RIGHT CONTROL & GUIDE PANEL ──────────────────────────────────────────
    function showPremiumNotification(message, duration = 3000) {
        let container = document.getElementById("premium-notif-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "premium-notif-container";
            document.body.appendChild(container);
        }
        const toast = document.createElement("div");
        toast.className = "premium-toast";
        toast.innerHTML = `<i class="fa-solid fa-circle-info" style="color: var(--color-blue);"></i> <span>${message}</span>`;
        container.appendChild(toast);
        
        // Force reflow
        toast.offsetHeight;
        
        toast.classList.add("show");
        
        setTimeout(() => {
            toast.classList.remove("show");
            toast.classList.add("hide");
            toast.addEventListener("transitionend", () => {
                toast.remove();
            });
        }, duration);
    }

    function updateRightPanelAIScore(score) {
        const aiScoreValue = document.getElementById("ai-score-value");
        if (!aiScoreValue) return;
        const numScore = parseFloat(score);
        if (isNaN(numScore)) return;
        
        aiScoreValue.textContent = `%${numScore.toFixed(1)}`;
        if (numScore >= 80) {
            aiScoreValue.style.color = "var(--color-green)";
        } else if (numScore >= 60) {
            aiScoreValue.style.color = "var(--color-gold)";
        } else {
            aiScoreValue.style.color = "var(--color-red)";
        }
    }

    function setupRightPanel() {
        const rightPanel = document.getElementById("app-right-panel");
        const btnToggle = document.getElementById("btn-toggle-right-panel");
        const btnClose = document.getElementById("btn-close-right-panel");
        
        if (!rightPanel) return;

        // Toggle panel open/close
        if (btnToggle) {
            btnToggle.addEventListener("click", (e) => {
                e.stopPropagation();
                rightPanel.classList.toggle("active");
            });
        }
        
        if (btnClose) {
            btnClose.addEventListener("click", () => {
                rightPanel.classList.remove("active");
            });
        }

        // Close on Esc key
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                rightPanel.classList.remove("active");
            }
        });

        // Close on click outside
        document.addEventListener("click", (e) => {
            if (rightPanel.classList.contains("active") && 
                !rightPanel.contains(e.target) && 
                (!btnToggle || !btnToggle.contains(e.target))) {
                rightPanel.classList.remove("active");
            }
        });

        // Accordion for Guide
        const accordionHeaders = rightPanel.querySelectorAll(".accordion-header");
        accordionHeaders.forEach(header => {
            header.addEventListener("click", (e) => {
                e.stopPropagation();
                const item = header.parentElement;
                const isActive = item.classList.contains("active");
                
                // Close all other items
                rightPanel.querySelectorAll(".accordion-item").forEach(itm => {
                    itm.classList.remove("active");
                    itm.querySelector(".accordion-content").style.maxHeight = null;
                });
                
                if (!isActive) {
                    item.classList.add("active");
                    const content = item.querySelector(".accordion-content");
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            });
        });

        // Theme Switcher
        const themeSelect = document.getElementById("right-panel-theme");
        function applyTheme(themeName) {
            document.body.classList.remove("theme-ocean-blue", "theme-slate-gray");
            if (themeName === "ocean-blue") {
                document.body.classList.add("theme-ocean-blue");
            } else if (themeName === "slate-gray") {
                document.body.classList.add("theme-slate-gray");
            }
            localStorage.setItem("app-theme", themeName);
            if (themeSelect) {
                themeSelect.value = themeName;
            }
        }
        
        if (themeSelect) {
            // Load saved theme
            const savedTheme = localStorage.getItem("app-theme") || "neon-dark";
            applyTheme(savedTheme);

            themeSelect.addEventListener("change", (e) => {
                const selected = e.target.value;
                applyTheme(selected);
                const displayNames = {
                    "neon-dark": "Neon Dark",
                    "ocean-blue": "Okyanus Mavisi",
                    "slate-gray": "Klasik Gri"
                };
                showPremiumNotification(`Tema '${displayNames[selected] || selected}' olarak güncellendi.`);
            });
        }

        // AI Karar Hassasiyeti (Model Version) Switcher
        const modelVersionSelect = document.getElementById("right-panel-model-version");
        if (modelVersionSelect) {
            modelVersionSelect.addEventListener("change", (e) => {
                const val = e.target.value;
                showPremiumNotification(`AI Karar Hassasiyeti güncellendi: ${val === "zeki_eleme" ? "Zeki Eleme" : "Tüm Öznitelikler"}`);
            });
        }

        // Active Currency Sync (initial and changes)
        const currencyIndicator = document.getElementById("right-panel-currency-indicator");
        const globalCurrencySelect = document.getElementById("global-currency");
        
        if (currencyIndicator) {
            if (globalCurrencySelect) {
                currencyIndicator.textContent = globalCurrencySelect.value;
                globalCurrencySelect.addEventListener("change", (e) => {
                    currencyIndicator.textContent = e.target.value;
                });
            }
        }

        // Ortalama Çizgisi Senkronizasyonu
        const rightPanelShowAvg = document.getElementById("right-panel-show-avg");
        if (rightPanelShowAvg) {
            rightPanelShowAvg.addEventListener("change", () => {
                const checked = rightPanelShowAvg.checked;
                
                const trendShowAvg = document.getElementById("trend-show-avg");
                if (trendShowAvg) {
                    trendShowAvg.checked = checked;
                    trendShowAvg.dispatchEvent(new Event("change"));
                }
                
                const regTrendShowAvg = document.getElementById("reg-trend-show-avg");
                if (regTrendShowAvg) {
                    regTrendShowAvg.checked = checked;
                    regTrendShowAvg.dispatchEvent(new Event("change"));
                }
                
                showPremiumNotification(`Sektör Ortalaması gösterimi ${checked ? "aktif" : "pasif"} yapıldı.`);
            });

            // Bidirectional sync: listen to other checkboxes to update right panel state
            const trendShowAvg = document.getElementById("trend-show-avg");
            if (trendShowAvg) {
                trendShowAvg.addEventListener("change", () => {
                    if (rightPanelShowAvg.checked !== trendShowAvg.checked) {
                        rightPanelShowAvg.checked = trendShowAvg.checked;
                    }
                });
            }

            const regTrendShowAvg = document.getElementById("reg-trend-show-avg");
            if (regTrendShowAvg) {
                regTrendShowAvg.addEventListener("change", () => {
                    if (rightPanelShowAvg.checked !== regTrendShowAvg.checked) {
                        rightPanelShowAvg.checked = regTrendShowAvg.checked;
                    }
                });
            }
        }
    }

    // Setup ResizeObserver for charts in resizable containers
    if (typeof ResizeObserver !== 'undefined') {
        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                const canvas = entry.target.querySelector('canvas');
                if (canvas && canvas.chartInstance) {
                    canvas.chartInstance.resize();
                }
            }
        });
        document.querySelectorAll('.canvas-container').forEach(container => {
            resizeObserver.observe(container);
        });
        window.chartResizeObserver = resizeObserver;
    }

    // Initialize Right Panel
    setupRightPanel();
});
