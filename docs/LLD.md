# ML Platform — LLD summary

Architecture and design reference for the multi-account SageMaker governance platform in this repository.

## Diagrams

| Artifact | Path |
|----------|------|
| Editable draw.io | `assets/ML_Platform_LLD.drawio` |
| End-to-end flowchart | `assets/ML_Platform_Flowchart.png` |
| PPT (AWS icons) | `assets/ML_Platform_Consolidated_LLD.pptx` |

Regenerate:

```bash
python scripts/build_reference_drawio.py
python scripts/build_flowchart.py
python scripts/build_reference_lld_ppt.py
```

## Document sections

1. Purpose and scope  
2. Architecture overview (reference diagram + numbered flows)  
2.4 End-to-end flowchart  
3. Account topology + AWS CFN deployment steps  
4. DEV environment detailed LLD  
5. PROD environment detailed LLD  
6. Model project template + pipeline factory  
7. CI/CD workflows  
8. Central governance stack  
9. Interface register (IF-ML-01 … IF-ML-14)  
10. Data and artifact design  
11. Infrastructure (ML-Platform repo + Terraform)  
12. IAM roles  
13. Serving + event contracts  
14. Security  
15. Observability and runbooks  
16. HA / DR  
17. NFRs  
18. Delivery phases + RACI  
19. Open questions  
20. References  
