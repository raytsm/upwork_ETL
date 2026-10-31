## Four specific problems caused by buggy database/scraper export
- multiline job descriptions
- double quotes escaped as '" instead of "" so '" is replaced with '""
- for odd number of single quotes, it belongs to '" category so problem 2 handles it, for even number of single quotes " is real closing quotes so it remains as it is
- comma inside raw json is treaded as separate columns so {} opening and closing curly brackets are searched and proper json is formed