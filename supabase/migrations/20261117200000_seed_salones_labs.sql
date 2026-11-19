INSERT INTO public.salon (nombre, capacidad, estado, ubicacion)
SELECT v.nombre, 20, 'disponible', v.ubicacion
FROM (
    VALUES
        ('Sala1', 'Sede:CLS Edificio:O'),
        ('Sala2', 'Sede:CLS Edificio:O'),
        ('Sala3', 'Sede:CLS Edificio:O'),
        ('Sala4', 'Sede:CLS Edificio:O'),
        ('Sala5', 'Sede:CLS Edificio:O'),
        ('Sala6', 'Sede:CLS Edificio:O'),
        ('Sala7', 'Sede:CLS Edificio:O'),
        ('Sala8', 'Sede:CLS Edificio:O'),
        ('Sala9', 'Sede:CLS Edificio:O'),
        ('Sala10', 'Sede:CLS Edificio:O'),
        ('Lab1', 'Sede:CLS Edificio:O'),
        ('Lab2', 'Sede:CLS Edificio:O'),
        ('Lab3', 'Sede:CLS Edificio:O'),
        ('Lab4', 'Sede:CLS Edificio:O'),
        ('Lab5', 'Sede:CLS Edificio:O'),
        ('Lab6', 'Sede:CLS Edificio:O'),
        ('Lab7', 'Sede:CLS Edificio:O'),
        ('Lab8', 'Sede:CLS Edificio:O'),
        ('Lab9', 'Sede:CLS Edificio:O'),
        ('Lab10', 'Sede:CLS Edificio:O')
) AS v(nombre, ubicacion)
WHERE NOT EXISTS (
    SELECT 1 FROM public.salon s WHERE lower(s.nombre) = lower(v.nombre)
);
