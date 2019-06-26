# Flask FreeGenes

Welcome to the Flask FreeGenes application. 

flask run --host=0.0.0.0

# bugs
- fastq file upload takes too long

## Notes
- You must upload file independently and first before applying it to a fastq or pileup
```
file_to_send = '/home/koeng/Downloads/MMSYN1_0003_1.pileup'
url= 'http://127.0.0.1:5000/files/upload'
payload = {"name": "MMSYN1_0003_1.pileup"}
files = {
     'json': ('json_file', json.dumps(payload), 'application/json'),
     'file': (os.path.basename(file_to_send), open(file_to_send, 'rb'), 'application/octet-stream')
}
r = requests.post(url, files=files,auth=())
```

`psql -d '' -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'`


# Virtual build definition
The virtual build definition (vbd) is a string based definition of a what a composite is and how it can be used, based off of a a list of primitives. The purpose of the vbd is for a human operator to be able to quickly read composite gene definitions and learn how they were composed. 

Every part should contain a vbd for language-agnostic tracking of parts.

`{bbsi-GAGG}.[GeneID].AATG.[GeneID].{CTAG-bbsi}_[(Vector)]`

- Brackets surround the GeneID unit
- Period dots are used to denote sequence links between different parts. Sequence links are always upper case.
- The 2 outer sequence links are surrounded by curly brackets to denotate which direction their respective restriction enzyme cuts. Restriction enzymes are always lower case. Commas can be used to denote 2 different restriction enzymes.
- An underscore connects to the vector backbone, which is defined with the same method as a GeneID unit. 

- A vector may represent itself 

Examples:
- pOpen_v3.0
`{GGAG-bbsi,GGAG-btgzi}.[].{bbsi-CGCT,btgzi-CGCT}_{AGAG-aari}.[BBF10K_003241].{aari-GTCA}`

- A part inserted into pOpen_v3.0
`{bsai-AATG}.[BBF10K_000003].{GCTT-bsai,TCC-sapi}_{AGAG-aari}.[pOpen_v3.0].{aari-GTCA}`

- A simple composite
`{bsmbi-GATG}.GGAG.[full_promoter].AATG.[cds].GCTT.[terminator].CGCT.{CAGT-bsmbi}_{AGAG-aari}.[pOpen_v3.0].{aari-GTCA}`


# reserved tags
- strain: [ccdB_res]
- marker: [gfp]
- resistance: [ampicillin]
- vector: [primitive, composite]
- target_organism: [yeast, ecoli]
